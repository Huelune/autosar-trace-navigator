"""Restricted C object access paths; no array evaluation or alias resolution."""

from dataclasses import dataclass
import re


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


@dataclass(frozen=True)
class AccessPath:
    """Keep the root object and every member operator distinct from member names."""

    root: str
    members: tuple[tuple[str, str], ...] = ()
    dereference: bool = False

    @property
    def expression(self) -> str:
        return ("*" if self.dereference else "") + self.root + "".join(op + name for op, name in self.members)

    @property
    def indirect(self) -> bool:
        return self.dereference or any(op == "->" for op, _ in self.members)

    def relative_to(self, prefix: "AccessPath") -> "AccessPath | None":
        """Project a write to an enclosing object onto the requested member."""
        if self.root != prefix.root:
            return None
        if prefix.dereference:
            if self == prefix:
                return AccessPath("value")
            if self.members and self.members[0][0] == "->":
                return AccessPath("value", ((".", self.members[0][1]), *self.members[1:]))
            return None
        if self.members[:len(prefix.members)] != prefix.members:
            return None
        if prefix.members and self.dereference:
            return None
        return AccessPath("value", self.members[len(prefix.members):], self.dereference)


def parse_access_path(expression: str) -> AccessPath | None:
    """Accept identifiers, nested . / -> members, and a single explicit *pointer."""
    if not isinstance(expression, str):
        return None
    if not re.fullmatch(r"\s*(?:\*\s*)?" + _IDENTIFIER + r"(?:\s*(?:\.|->)\s*" + _IDENTIFIER + r")*\s*", expression):
        return None
    text = re.sub(r"\s+", "", expression)
    if re.fullmatch(r"\*" + _IDENTIFIER, text):
        return AccessPath(text[1:], dereference=True)
    if not re.fullmatch(_IDENTIFIER + r"(?:(?:\.|->)" + _IDENTIFIER + r")*", text):
        return None
    root = re.match(_IDENTIFIER, text).group()
    return AccessPath(root, tuple(re.findall(r"(\.|->)(" + _IDENTIFIER + r")", text[len(root):])))


def parse_return_path(expression: str) -> AccessPath | None:
    """Use the existing return probe kind to preserve a projected aggregate return."""
    if not isinstance(expression, str) or not (expression == "$return" or expression.startswith(("$return.", "$return->"))):
        return None
    return parse_access_path("value" + expression[len("$return"):])
