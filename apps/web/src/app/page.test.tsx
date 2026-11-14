import { render, screen } from "@testing-library/react";
import HomePage from "./page";

describe("HomePage", () => {
  it("shows the product name and its promise", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "Tekki-Pass" })).toBeInTheDocument();
    expect(screen.getByText(/preuve de travail vérifiable/i)).toBeInTheDocument();
  });
});
