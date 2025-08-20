class SearchError(Exception):
    """Base exception for search-related errors"""
    pass


class InvalidFilterFieldError(SearchError):
    """Raised when a filter field is not valid for the model"""
    
    def __init__(self, field_name: str, model_name: str):
        self.field_name = field_name
        self.model_name = model_name
        super().__init__(f"Field '{field_name}' is not a valid filter field for model '{model_name}'")


class InvalidSortFieldError(SearchError):
    """Raised when a sort field is not valid for the model"""
    
    def __init__(self, field_name: str, model_name: str):
        self.field_name = field_name
        self.model_name = model_name
        super().__init__(f"Field '{field_name}' is not a valid sort field for model '{model_name}'")


class InvalidSearchFieldError(SearchError):
    """Raised when search is attempted on a model without searchable fields configured"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(f"No searchable fields configured for model '{model_name}'")


class FilterValueError(SearchError):
    """Raised when a filter value cannot be converted to the expected type"""
    
    def __init__(self, field_name: str, value: str, expected_type: str):
        self.field_name = field_name
        self.value = value
        self.expected_type = expected_type
        super().__init__(
            f"Cannot convert value '{value}' to {expected_type} for field '{field_name}'"
        )