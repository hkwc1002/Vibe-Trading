import { describe, expect, it } from "vitest";
import { formatCnySmart, formatCnyYi, formatPctDecimal, formatRatio } from "../lowAbsorbFormat";

describe("lowAbsorbFormat", () => {
  it("formats raw CNY values into yi", () => {
    expect(formatCnyYi(612000000000)).toBe("6120.0 亿");
    expect(formatCnyYi("42600000000")).toBe("426.0 亿");
    expect(formatCnyYi(-120000000)).toBe("-1.2 亿");
  });

  it("formats smart CNY ranges", () => {
    expect(formatCnySmart(1200000000)).toBe("12.0 亿");
    expect(formatCnySmart(120000)).toBe("12.0 万");
    expect(formatCnySmart(12)).toBe("12.00 元");
  });

  it("formats percentage decimals and ratios", () => {
    expect(formatPctDecimal(0.018)).toBe("1.80%");
    expect(formatRatio(1.234)).toBe("1.23");
  });
});
