from enum import Enum


class PostAction(Enum):
    GOOD_POST = "good_post"
    DELETE_POST = "delete_post"
    UNSURE_POST = "unsure_post"
    END_SEARCH = "end_search"


class SearchAction(Enum):
    POST = "post"
    CANCEL = "cancel"
