/**
 * Sign-in.
 *
 * These cover the gap that made the report wizard unusable: the API required
 * a session and the web app had no way to start one. What matters here is
 * that a person can always reach a working door — the Google button is
 * offered only when the API can actually complete the flow, the email path
 * still works when it cannot, and a failed Google callback comes back with a
 * reason rather than a blank page.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SignInPanel } from "@/components/auth/SignInPanel";

let calls: { url: string; init: RequestInit | undefined }[] = [];

function mockFetch(options: { google?: boolean; signInStatus?: number } = {}) {
  const { google = true, signInStatus = 202 } = options;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      const href = String(url);
      calls.push({ url: href, init });

      if (href.includes("/auth/providers")) {
        return new Response(JSON.stringify({ google, magic_link: true }), {
          status: 200,
        });
      }
      if (href.includes("/auth/sign-in")) {
        if (signInStatus !== 202) {
          return new Response(
            JSON.stringify({
              error: {
                code: "RATE_LIMITED",
                message: "요청이 너무 잦습니다.",
                request_id: "req-1",
                details: {},
              },
            }),
            { status: signInStatus },
          );
        }
        return new Response(
          JSON.stringify({ message: "보냈습니다.", dev_token: "dev-token-abc" }),
          { status: 202 },
        );
      }
      return new Response("{}", { status: 200 });
    }),
  );
}

beforeEach(() => {
  calls = [];
});

describe("SignInPanel", () => {
  it("offers Google when the API says it is configured", async () => {
    mockFetch({ google: true });
    render(<SignInPanel next="/report/new" callbackError={null} />);

    const button = await screen.findByRole("link", {
      name: /구글 계정으로 계속하기/,
    });
    // A full navigation to the API origin, not a fetch — the flow leaves the
    // app for Google and returns to the API's callback.
    expect(button.getAttribute("href")).toContain("/auth/google/start");
    // Where to land afterwards rides along.
    expect(button.getAttribute("href")).toContain(
      `next=${encodeURIComponent("/report/new")}`,
    );
  });

  it("hides the Google button when the API has no credentials", async () => {
    // Otherwise the page offers a button that leads nowhere — the exact
    // dead end this whole surface exists to remove.
    mockFetch({ google: false });
    render(<SignInPanel next="/" callbackError={null} />);

    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: /구글 계정으로 계속하기/ }),
      ).not.toBeInTheDocument();
    });
    // The email path is still there, so sign-in never becomes impossible.
    expect(screen.getByLabelText("이메일로 로그인")).toBeInTheDocument();
  });

  it("still offers the email path alongside Google", async () => {
    mockFetch({ google: true });
    render(<SignInPanel next="/" callbackError={null} />);

    await screen.findByRole("link", { name: /구글 계정으로 계속하기/ });
    expect(screen.getByLabelText("이메일로 로그인")).toBeInTheDocument();
  });

  it("requests a magic link and confirms where it went", async () => {
    mockFetch();
    render(<SignInPanel next="/" callbackError={null} />);

    await userEvent.type(screen.getByLabelText("이메일로 로그인"), "dodo@example.com");
    await userEvent.click(screen.getByRole("button", { name: "링크 받기" }));

    expect(await screen.findByText(/dodo@example.com로 로그인 링크를 보냈습니다/))
      .toBeInTheDocument();

    const signIn = calls.find((c) => c.url.includes("/auth/sign-in"));
    expect(signIn?.init?.method).toBe("POST");
    expect(JSON.parse(String(signIn?.init?.body))).toEqual({
      email: "dodo@example.com",
    });
  });

  it("surfaces a rate limit in plain Korean rather than a code", async () => {
    mockFetch({ signInStatus: 429 });
    render(<SignInPanel next="/" callbackError={null} />);

    await userEvent.type(screen.getByLabelText("이메일로 로그인"), "dodo@example.com");
    await userEvent.click(screen.getByRole("button", { name: "링크 받기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "로그인 요청이 너무 잦습니다",
    );
  });

  it("explains why Google sent the user back", async () => {
    // The callback redirects here with a reason instead of rendering an
    // error envelope the browser would show as raw JSON.
    mockFetch();
    render(<SignInPanel next="/" callbackError="cancelled" />);

    expect(screen.getByRole("alert")).toHaveTextContent("구글 로그인이 취소되었습니다");
  });

  it("falls back to a generic reason for an unrecognized callback error", async () => {
    mockFetch();
    render(<SignInPanel next="/" callbackError="something-new" />);

    expect(screen.getByRole("alert")).toHaveTextContent("구글 로그인을 완료하지 못했습니다");
  });
});
