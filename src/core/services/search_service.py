from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from decimal import Decimal
from sqlalchemy import Select, and_, or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InspectionAttr, selectinload
from pydantic import BaseModel
from loguru import logger

from src.core.schemas.search import (
    BaseSearchRequestBody, 
    FilterOperator, 
    SearchResponse,
    BaseFilterItem,
    BaseSortItem
)
from src.core.exceptions.search import (
    InvalidFilterFieldError,
    InvalidSortFieldError, 
    InvalidSearchFieldError,
    FilterValueError
)

T = TypeVar('T')
ModelT = TypeVar('ModelT')
ResponseT = TypeVar('ResponseT', bound=BaseModel)


class SearchConfig:
    """Configuration class for search functionality"""
    
    def __init__(
        self,
        simple_columns: List[str],
        join_columns: Optional[Dict[str, Dict[str, Any]]] = None,
        searchable_columns: Optional[List[str]] = None,
        sortable_columns: Optional[List[str]] = None
    ):
        self.simple_columns = simple_columns
        self.join_columns = join_columns or {}
        self.searchable_columns = searchable_columns or []
        self.sortable_columns = sortable_columns or simple_columns


class UniversalSearchService(Generic[ModelT, ResponseT]):
    """Universal search service for SQLAlchemy models with filtering, sorting, and pagination"""
    
    def __init__(
        self,
        model: Type[ModelT],
        config: SearchConfig,
        session: AsyncSession,
        response_model: Type[ResponseT]
    ):
        self.model = model
        self.config = config
        self.session = session
        self.response_model = response_model
        
    async def search(
        self, 
        request_body: BaseSearchRequestBody,
        workspace_id: Optional[int] = None
    ) -> SearchResponse[ResponseT]:
        """
        Perform search with filtering, sorting, and pagination
        
        Args:
            request_body: Search request containing filters, sorts, pagination
            workspace_id: Optional workspace ID for scoped queries
            
        Returns:
            SearchResponse with items and pagination metadata
        """
        try:
            # Build base query
            query = select(self.model)
            
            # For Product model, include stock relationship
            if self.model.__name__ == 'Product':
                query = query.options(selectinload(self.model.catalog_stocks))
            
            # Add workspace filtering if provided
            if workspace_id is not None and hasattr(self.model, 'workspace_id'):
                query = query.where(self.model.workspace_id == workspace_id)
            
            # Handle joins for complex filtering
            joined_tables = set()
            if request_body.filter:
                query, joined_tables = self._add_joins_for_filters(query, request_body.filter)
            
            # Apply search
            if request_body.search:
                query = self._apply_search(query, request_body.search)
                
            # Apply filters
            if request_body.filter:
                query = self._apply_filters(query, request_body.filter)
                
            # Apply sorting
            if request_body.sort:
                query = self._apply_sorting(query, request_body.sort, joined_tables)
            else:
                # Default sorting by id asc
                query = query.order_by(self.model.id.asc())
                
            # Get total count before pagination
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination
            page = request_body.page or 1
            page_size = request_body.page_size or 20
            offset = (page - 1) * page_size
            
            query = query.offset(offset).limit(page_size)
            
            # Execute query
            logger.debug(f"Executing search query: {query}")
            result = await self.session.execute(query)
            items = result.scalars().all()
            
            # Convert to response models
            response_items = []
            for item in items:
                # For Product model, we need special handling for stock field
                if hasattr(item, '__table__') and item.__class__.__name__ == 'Product':
                    # Handle Product model with stock calculation
                    stock_quantity = 0
                    if hasattr(item, 'catalog_stocks') and item.catalog_stocks:
                        stock_quantity = item.catalog_stocks[0].quantity
                    
                    item_dict = {
                        column.name: getattr(item, column.name) 
                        for column in item.__table__.columns
                    }
                    item_dict['stock'] = stock_quantity
                    response_items.append(self.response_model.model_validate(item_dict))
                elif hasattr(item, '__dict__'):
                    # Convert other SQLAlchemy models to dict then to Pydantic model
                    item_dict = {
                        column.name: getattr(item, column.name) 
                        for column in item.__table__.columns
                    }
                    response_items.append(self.response_model.model_validate(item_dict))
                else:
                    response_items.append(self.response_model.model_validate(item))
            
            return SearchResponse.create(
                items=response_items,
                total=total,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error(f"Search error for model {self.model.__name__}: {e}")
            raise
    
    def _add_joins_for_filters(
        self, 
        query: Select, 
        filters: List[BaseFilterItem]
    ) -> tuple[Select, set]:
        """Add necessary joins for filters that require them"""
        joined_tables = set()
        
        for filter_item in filters:
            if filter_item.column in self.config.join_columns:
                join_config = self.config.join_columns[filter_item.column]
                join_target = join_config.get('join')
                
                if join_target and join_target not in joined_tables:
                    query = query.join(join_target)
                    joined_tables.add(join_target)
                    
        return query, joined_tables
    
    def _apply_search(self, query: Select, search_term: str) -> Select:
        """Apply search across searchable columns"""
        if not self.config.searchable_columns:
            raise InvalidSearchFieldError(self.model.__name__)
            
        search_conditions = []
        normalized_search = search_term.strip().lower()
        
        for column_name in self.config.searchable_columns:
            if column_name in self.config.simple_columns:
                # Simple column search
                column = getattr(self.model, column_name)
                search_conditions.append(
                    func.lower(column).contains(normalized_search)
                )
            elif column_name in self.config.join_columns:
                # Join column search
                join_config = self.config.join_columns[column_name]
                target_column = join_config.get('column')
                if target_column:
                    search_conditions.append(
                        func.lower(target_column).contains(normalized_search)
                    )
        
        if search_conditions:
            query = query.where(or_(*search_conditions))
            
        return query
    
    def _apply_filters(self, query: Select, filters: List[BaseFilterItem]) -> Select:
        """Apply filters to the query"""
        filter_conditions = []
        
        for filter_item in filters:
            try:
                condition = self._build_filter_condition(filter_item)
                if condition is not None:
                    filter_conditions.append(condition)
            except Exception as e:
                logger.error(f"Error building filter for {filter_item.column}: {e}")
                raise FilterValueError(
                    filter_item.column, 
                    filter_item.value, 
                    "valid filter value"
                )
        
        if filter_conditions:
            query = query.where(and_(*filter_conditions))
            
        return query
    
    def _build_filter_condition(self, filter_item: BaseFilterItem):
        """Build SQLAlchemy condition for a single filter"""
        column_name = filter_item.column
        value = filter_item.value
        operator = filter_item.operator
        
        # Validate column exists
        if (column_name not in self.config.simple_columns and 
            column_name not in self.config.join_columns):
            raise InvalidFilterFieldError(column_name, self.model.__name__)
        
        # Get the actual column
        if column_name in self.config.simple_columns:
            column = getattr(self.model, column_name)
        else:
            # Join column
            join_config = self.config.join_columns[column_name]
            column = join_config.get('column')
            
        if column is None:
            raise InvalidFilterFieldError(column_name, self.model.__name__)
        
        # Convert value based on column type
        converted_value = self._convert_filter_value(column, value, column_name)
        
        # Build condition based on operator
        if operator == FilterOperator.EQUALS:
            return column == converted_value
        elif operator == FilterOperator.NOT_EQUALS:
            return column != converted_value
        elif operator == FilterOperator.CONTAINS:
            return func.lower(column).contains(func.lower(converted_value))
        elif operator == FilterOperator.DOES_NOT_CONTAIN:
            return ~func.lower(column).contains(func.lower(converted_value))
        elif operator == FilterOperator.STARTS_WITH:
            return func.lower(column).startswith(func.lower(converted_value))
        elif operator == FilterOperator.ENDS_WITH:
            return func.lower(column).endswith(func.lower(converted_value))
        elif operator == FilterOperator.IS_EMPTY:
            return or_(column.is_(None), column == '')
        elif operator == FilterOperator.IS_NOT_EMPTY:
            return and_(column.is_not(None), column != '')
        elif operator == FilterOperator.GREATER_THAN:
            return column > converted_value
        elif operator == FilterOperator.LESS_THAN:
            return column < converted_value
        elif operator == FilterOperator.GREATER_OR_EQUAL:
            return column >= converted_value
        elif operator == FilterOperator.LESS_OR_EQUAL:
            return column <= converted_value
        elif operator == FilterOperator.IN:
            values = [v.strip() for v in value.split(',')]
            converted_values = [
                self._convert_filter_value(column, v, column_name) for v in values
            ]
            return column.in_(converted_values)
        elif operator == FilterOperator.NOT_IN:
            values = [v.strip() for v in value.split(',')]
            converted_values = [
                self._convert_filter_value(column, v, column_name) for v in values
            ]
            return ~column.in_(converted_values)
            
        return None
    
    def _convert_filter_value(self, column, value: str, column_name: str):
        """Convert string value to appropriate type based on column type"""
        if hasattr(column.type, 'python_type'):
            python_type = column.type.python_type
            
            try:
                if python_type == int:
                    return int(value)
                elif python_type == float:
                    return float(value)
                elif python_type == Decimal:
                    return Decimal(value)
                elif python_type == bool:
                    return value.lower() in ('true', '1', 'yes', 'on')
                else:
                    return str(value).strip()
            except (ValueError, TypeError) as e:
                raise FilterValueError(column_name, value, python_type.__name__)
        
        return str(value).strip()
    
    def _apply_sorting(
        self, 
        query: Select, 
        sorts: List[BaseSortItem],
        joined_tables: set
    ) -> Select:
        """Apply sorting to the query"""
        for sort_item in sorts:
            column_name = sort_item.column
            
            # Validate sortable column
            if (column_name not in self.config.sortable_columns and 
                column_name not in self.config.join_columns):
                raise InvalidSortFieldError(column_name, self.model.__name__)
            
            # Get column
            if column_name in self.config.simple_columns:
                column = getattr(self.model, column_name)
            elif column_name in self.config.join_columns:
                join_config = self.config.join_columns[column_name]
                column = join_config.get('column')
                
                # Ensure join is added if not already
                join_target = join_config.get('join')
                if join_target and join_target not in joined_tables:
                    query = query.join(join_target)
                    joined_tables.add(join_target)
            else:
                raise InvalidSortFieldError(column_name, self.model.__name__)
            
            # Apply sort direction
            if sort_item.direction.value == 'desc':
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
                
        return query