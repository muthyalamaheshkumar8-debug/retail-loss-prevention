import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { IncidentTable, Pager, VideoPlayer } from "./components";
import { clock, errorText } from "./api";
afterEach(cleanup);
describe("Investigation components", () => {
  it("links actual incidents to their investigation route", () => {
    render(
      <MemoryRouter>
        <IncidentTable
          items={[
            {
              id: "INC-123",
              camera_id: "Checkout",
              category: "other",
              timestamp: 77,
              priority: "high",
              status: "NEEDS_REVIEW",
            },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("INC-123")).toHaveAttribute(
      "href",
      "/incidents/INC-123",
    );
    expect(screen.getByText("01:17")).toBeInTheDocument();
    expect(screen.getByText("needs review")).toBeInTheDocument();
  });
  it("shows an honest empty queue", () => {
    render(<IncidentTable items={[]} />);
    expect(screen.getByText("Your queue is clear")).toBeInTheDocument();
  });
  it("bounds pagination at the first page", () => {
    const onChange = vi.fn();
    render(<Pager page={1} total={30} size={25} onChange={onChange} />);
    expect(screen.getByText("Previous")).toBeDisabled();
    fireEvent.click(screen.getByText("Next"));
    expect(onChange).toHaveBeenCalledWith(2);
  });
  it("seeks to the event timestamp and moves by ten seconds", () => {
    const ref = { current: null };
    render(
      <VideoPlayer
        src="/api/videos/real/media"
        eventTime={25}
        videoRef={ref}
      />,
    );
    Object.defineProperty(ref.current, "duration", { value: 100 });
    fireEvent.click(screen.getByText("Event 00:25"));
    expect(ref.current.currentTime).toBe(25);
    fireEvent.click(screen.getAllByText("10 sec")[0]);
    expect(ref.current.currentTime).toBe(15);
  });
  it("formats times and readable API validation errors", () => {
    expect(clock(277.2)).toBe("04:37");
    expect(
      errorText({ response: { status: 422, data: { detail: [] } } }),
    ).toContain("Check");
  });
});
