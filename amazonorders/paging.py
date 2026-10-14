__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict, Generic, List, Optional, TypeVar

from amazonorders.entity.parsable import Parsable

#: The entity type a :class:`PagedResults` holds.
ParsableT = TypeVar("ParsableT", bound=Parsable)


class PagedResults(Generic[ParsableT]):
    """
    One batch of results from a page-returning call, like
    :func:`~amazonorders.orders.AmazonOrders.get_order_history_page`, with the cursor to fetch the next batch.
    """

    def __init__(self,
                 items: List[ParsableT],
                 cursor: Optional[Dict[str, Any]]) -> None:
        #: The results in this batch.
        self.items: List[ParsableT] = items
        #: Pass this back as ``cursor`` to the same call to fetch the next batch. A JSON-safe ``dict`` to keep as
        #: it is, not to build or change. ``None`` when there are no more results.
        self.cursor: Optional[Dict[str, Any]] = cursor

    @property
    def has_more(self) -> bool:
        """
        ``True`` if there are more results to fetch with :attr:`cursor`.
        """
        return self.cursor is not None

    def to_dict(self,
                exclude_none: bool = False) -> Dict[str, Any]:
        """
        Serialize the batch to a ``dict`` of primitives, suitable for JSON, with each item serialized by its own
        :func:`~amazonorders.entity.parsable.Parsable.to_dict`.

        :param exclude_none: Passed to each item's ``to_dict``. :attr:`cursor` is kept either way, so
            ``"cursor": None`` still says there are no more results.
        :return: The ``items``, ``cursor``, and ``has_more``.
        """
        return {
            "items": [item.to_dict(exclude_none=exclude_none) for item in self.items],
            "cursor": self.cursor,
            "has_more": self.has_more,
        }
