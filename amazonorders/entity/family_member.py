__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import Optional

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.parsable import Parsable

logger = logging.getLogger(__name__)


class FamilyMember(Parsable):
    """
    A member of the Amazon Household whose Orders the account can view, such as a linked Teen account. Pass its
    :attr:`id` as ``family_member_id`` to :func:`~amazonorders.orders.AmazonOrders.get_order_history` to get their
    Orders.
    """

    def __init__(self,
                 parsed: Tag,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(parsed, config)

        #: The FamilyMember ID, Amazon's ``familyMemberId``.
        self.id: Optional[str] = self.safe_parse(self._parse_id)
        #: The FamilyMember name.
        self.name: Optional[str] = self.safe_parse(self._parse_name)

    def __repr__(self) -> str:
        return f"<FamilyMember {self.id}: \"{self.name}\">"

    def __str__(self) -> str:  # pragma: no cover
        return f"FamilyMember {self.id}: {self.name}"

    def _parse_id(self) -> Optional[str]:
        value = self.parsed.get(self.config.selectors.FAMILY_MEMBER_ID_ATTR)
        return str(value).strip() if value else None

    def _parse_name(self) -> Optional[str]:
        # Amazon renders a NUL byte between the name and the suffix, e.g. "Jane Doe\x00's Orders"
        value = self.parsed.text.replace("\x00", " ").strip()
        suffix = self.config.selectors.FIELD_FAMILY_MEMBER_NAME_SUFFIX
        if suffix and suffix in value:
            value = value.split(suffix)[0]
        return value.strip() or None
