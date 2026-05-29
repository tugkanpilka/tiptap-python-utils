"""SharedFamilies: canonical bodies grouped by sharedId."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Iterator, Mapping

from .. import codec
from ..contract import key
from ..exceptions import TiptapValidationError
from ..model import Node
from .fingerprint import fingerprint

if TYPE_CHECKING:
    from ..content import Content


@dataclass(frozen=True)
class SharedFamilies:
    """Canonical node bodies indexed by sharedId."""

    _bodies: Mapping[str, Node] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_content(cls, content: "Content") -> "SharedFamilies":
        bodies: dict[str, Node] = {}
        prints: dict[str, str] = {}
        for ref in content.refs(parseable=True):
            sid = ref.node.shared_id
            if not sid:
                continue
            fp = fingerprint(ref.node)
            if sid in prints and prints[sid] != fp:
                raise TiptapValidationError(
                    f"Conflicting node bodies detected for sharedId '{sid}'"
                )
            bodies.setdefault(sid, ref.node)
            prints.setdefault(sid, fp)
        return cls(MappingProxyType(bodies))

    def __contains__(self, shared_id: str) -> bool:
        return shared_id in self._bodies

    def __getitem__(self, shared_id: str) -> Node:
        return self._bodies[shared_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._bodies)

    def __len__(self) -> int:
        return len(self._bodies)

    def merge(self, target: Node) -> Node:
        """Return target rewritten from the canonical body.

        Preserves the target's per-copy identity (local id, sharedId) and its
        per-copy ``place`` discriminator. The family-identical ``shared`` core
        rides along from the canonical body unchanged.
        """
        canonical = self[target.shared_id]
        raw = canonical.raw()
        attrs = dict(raw.get(key.ATTRS, {}))
        attrs.pop(key.PLACE, None)
        if target.id:
            attrs[key.ID] = target.id
        if target.shared_id:
            attrs[key.SHARED_ID] = target.shared_id
        target_attrs = target.raw().get(key.ATTRS, {})
        if key.PLACE in target_attrs:
            attrs[key.PLACE] = target_attrs[key.PLACE]
        raw[key.ATTRS] = attrs
        return codec.read_node(raw)
