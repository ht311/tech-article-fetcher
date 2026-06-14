import { describe, it, expect } from "vitest";
import { validateFeedback } from "./preferences";

describe("validateFeedback", () => {
  it("returns null for valid good feedback", () => {
    expect(validateFeedback({ action: "good", url: "https://example.com", title: "Test", source: "Source" })).toBeNull();
  });

  it("returns null for valid bad feedback", () => {
    expect(validateFeedback({ action: "bad", url: "https://example.com", title: "Test", source: "Source" })).toBeNull();
  });

  it("rejects invalid action", () => {
    expect(validateFeedback({ action: "meh", url: "https://example.com", title: "Test", source: "Source" })).toMatch(/action/);
  });

  it("rejects missing action", () => {
    expect(validateFeedback({ url: "https://example.com", title: "Test", source: "Source" })).toMatch(/action/);
  });

  it("rejects missing url", () => {
    expect(validateFeedback({ action: "good", title: "Test", source: "Source" })).toMatch(/url/);
  });

  it("rejects empty url", () => {
    expect(validateFeedback({ action: "good", url: "", title: "Test", source: "Source" })).toMatch(/url/);
  });

  it("rejects missing title", () => {
    expect(validateFeedback({ action: "good", url: "https://example.com", source: "Source" })).toMatch(/title/);
  });

  it("rejects missing source", () => {
    expect(validateFeedback({ action: "good", url: "https://example.com", title: "Test" })).toMatch(/source/);
  });

  it("rejects non-object body", () => {
    expect(validateFeedback("string")).toMatch(/object/);
    expect(validateFeedback(null)).toMatch(/object/);
  });
});
