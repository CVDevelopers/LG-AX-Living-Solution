"""Tiny dependency-free SVG plotting for the offline-lab figures (§8.5).

matplotlib is not in the deploy or dev bundle (numpy-only ethos, §12.1); these figures are
committed, deterministic artifacts, so a small hand-rolled SVG writer is both lighter and more
reproducible than a plotting library. Coordinates are rounded so the output is byte-stable.

Figures are theme-aware: colours use CSS custom properties with light defaults and a
prefers-color-scheme dark override, so the same SVG reads on a light slide or a dark viewer.
"""

from dataclasses import dataclass

_STYLE = """
<style>
  .bg{fill:#ffffff}.axis{stroke:#444;stroke-width:1}.grid{stroke:#e5e7eb;stroke-width:1}
  .lbl{fill:#444;font:13px system-ui,sans-serif}.ttl{fill:#111;font:600 15px system-ui,sans-serif}
  .tick{fill:#666;font:11px system-ui,sans-serif}
  @media (prefers-color-scheme: dark){
    .bg{fill:#0f1115}.axis{stroke:#c9ced6}.grid{stroke:#2a2f3a}
    .lbl{fill:#c9ced6}.ttl{fill:#f3f4f6}.tick{fill:#9aa3b2}}
</style>
"""


def _n(v: float) -> float:
    return round(v, 2)


@dataclass
class Chart:
    """A single Cartesian panel; call the draw methods then ``render``."""

    width: int
    height: int
    xr: tuple[float, float]
    yr: tuple[float, float]
    pad_l: int = 60
    pad_b: int = 46
    pad_t: int = 34
    pad_r: int = 18

    def __post_init__(self) -> None:
        self._body: list[str] = []

    def _sx(self, x: float) -> float:
        x0, x1 = self.xr
        w = self.width - self.pad_l - self.pad_r
        return _n(self.pad_l + (x - x0) / (x1 - x0) * w)

    def _sy(self, y: float) -> float:
        y0, y1 = self.yr
        h = self.height - self.pad_t - self.pad_b
        return _n(self.height - self.pad_b - (y - y0) / (y1 - y0) * h)

    def polyline(self, pts: list[tuple[float, float]], color: str, width: float = 2.0) -> None:
        d = " ".join(f"{self._sx(x)},{self._sy(y)}" for x, y in pts)
        self._body.append(
            f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}"/>'
        )

    def points(self, pts: list[tuple[float, float]], color: str, r: float = 3.5) -> None:
        for x, y in pts:
            self._body.append(
                f'<circle cx="{self._sx(x)}" cy="{self._sy(y)}" r="{r}" fill="{color}"/>'
            )

    def bars(self, pairs: list[tuple[float, float]], w_data: float, color: str) -> None:
        for cx, top in pairs:
            x0, x1 = self._sx(cx - w_data / 2), self._sx(cx + w_data / 2)
            y0, y1 = self._sy(0.0), self._sy(top)
            self._body.append(
                f'<rect x="{min(x0, x1)}" y="{y1}" width="{abs(x1 - x0)}" '
                f'height="{abs(y0 - y1)}" fill="{color}" fill-opacity="0.75"/>'
            )

    def text(
        self, x_px: float, y_px: float, s: str, cls: str = "lbl", anchor: str = "middle"
    ) -> None:
        self._body.append(
            f'<text x="{_n(x_px)}" y="{_n(y_px)}" text-anchor="{anchor}" class="{cls}">{s}</text>'
        )

    def axes(self, xticks: list[float], yticks: list[float], xfmt="{:.0f}", yfmt="{:.0f}") -> None:
        x0p, x1p = self._sx(self.xr[0]), self._sx(self.xr[1])
        y0p, y1p = self._sy(self.yr[0]), self._sy(self.yr[1])
        for xt in xticks:
            px = self._sx(xt)
            self._body.append(f'<line x1="{px}" y1="{y1p}" x2="{px}" y2="{y0p}" class="grid"/>')
            self.text(px, y0p + 16, xfmt.format(xt), "tick")
        for yt in yticks:
            py = self._sy(yt)
            self._body.append(f'<line x1="{x0p}" y1="{py}" x2="{x1p}" y2="{py}" class="grid"/>')
            self.text(x0p - 8, py + 4, yfmt.format(yt), "tick", anchor="end")
        self._body.append(f'<line x1="{x0p}" y1="{y0p}" x2="{x1p}" y2="{y0p}" class="axis"/>')
        self._body.append(f'<line x1="{x0p}" y1="{y1p}" x2="{x0p}" y2="{y0p}" class="axis"/>')

    def render(
        self, title: str, xlabel: str, ylabel: str, legend: list[tuple[str, str]] = ()
    ) -> str:
        cx = (self.pad_l + self.width - self.pad_r) / 2
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}" font-family="system-ui">',
            _STYLE,
            f'<rect class="bg" x="0" y="0" width="{self.width}" height="{self.height}"/>',
            f'<text x="{_n(cx)}" y="20" text-anchor="middle" class="ttl">{title}</text>',
            *self._body,
            f'<text x="{_n(cx)}" y="{self.height - 8}" text-anchor="middle" '
            f'class="lbl">{xlabel}</text>',
            f'<text x="16" y="{_n(self.height / 2)}" text-anchor="middle" class="lbl" '
            f'transform="rotate(-90 16 {_n(self.height / 2)})">{ylabel}</text>',
        ]
        for i, (label, color) in enumerate(legend):
            ly = self.pad_t + 6 + i * 18
            lx = self.width - self.pad_r - 150
            parts.append(f'<rect x="{lx}" y="{ly - 9}" width="12" height="12" fill="{color}"/>')
            parts.append(
                f'<text x="{lx + 18}" y="{ly + 1}" class="tick" text-anchor="start">{label}</text>'
            )
        parts.append("</svg>")
        return "\n".join(parts) + "\n"
