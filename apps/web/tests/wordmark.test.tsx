/**
 * The wordmark's accessibility contract.
 *
 * Two of the nine letters are drawn as SVG rather than set as type, so the
 * text layer on its own spells "GhostDd". The mark is therefore decorative and
 * the accessible name has to come from whatever wraps it. If someone ever
 * un-hides the wordmark, screen readers start announcing a misspelling of the
 * brand — these tests catch that.
 *
 * The other half of the contract, the `aria-label` on the header's home link,
 * is not covered here: `SiteHeader` pulls in `SessionNav`, which calls
 * `useRouter`, and this suite has no app-router harness to give it.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Wordmark } from "@/components/brand/Wordmark";

describe("Wordmark", () => {
  it("is hidden from assistive technology", () => {
    const { container } = render(<Wordmark />);
    const mark = container.firstElementChild;

    expect(mark).not.toBeNull();
    expect(mark).toHaveAttribute("aria-hidden", "true");
  });

  it("draws both o's of Dodo rather than setting them as type", () => {
    const { container } = render(<Wordmark />);

    expect(container.querySelectorAll("svg")).toHaveLength(2);
    expect(container.textContent).toBe("GhostDd");
  });
});
