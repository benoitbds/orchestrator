import React from "react";
import { render, waitFor } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/firebase", () => ({ auth: { currentUser: null } }));
vi.mock("firebase/auth", () => ({ onAuthStateChanged: vi.fn() }));

import { apiFetch } from "@/lib/api";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged } from "firebase/auth";
import { ProjectProvider, useProjects } from "@/context/ProjectContext";

const apiFetchMock = apiFetch as unknown as ReturnType<typeof vi.fn>;
const authMock = auth as { currentUser: any };
const onAuthStateChangedMock = onAuthStateChanged as unknown as ReturnType<typeof vi.fn>;

describe("ProjectProvider auth gating", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    onAuthStateChangedMock.mockReset();
    authMock.currentUser = null;
  });

  const TestChild = () => {
    const { projects } = useProjects();
    return <div data-testid="count">{projects.length}</div>;
  };

  it("does not fetch when signed out", async () => {
    onAuthStateChangedMock.mockImplementation((authArg, cb) => {
      cb(null);
      return () => {};
    });

    const { getByTestId } = render(
      <ProjectProvider>
        <TestChild />
      </ProjectProvider>
    );

    await waitFor(() => expect(onAuthStateChangedMock).toHaveBeenCalled());
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(getByTestId("count").textContent).toBe("0");
  });

  it("fetches projects after sign-in", async () => {
    onAuthStateChangedMock.mockImplementation((authArg, cb) => {
      authMock.currentUser = { uid: "u1" } as any;
      cb(authMock.currentUser);
      return () => {};
    });
    apiFetchMock.mockResolvedValue({ ok: true, json: async () => [{ id: 1, name: "P1" }] });

    const { getByTestId } = render(
      <ProjectProvider>
        <TestChild />
      </ProjectProvider>
    );

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getByTestId("count").textContent).toBe("1"));
  });

  it("clears projects on sign-out", async () => {
    let cb: (u: any) => void = () => {};
    onAuthStateChangedMock.mockImplementation((authArg, callback) => {
      cb = callback;
      return () => {};
    });
    apiFetchMock.mockResolvedValue({ ok: true, json: async () => [{ id: 1, name: "P1" }] });

    const { getByTestId } = render(
      <ProjectProvider>
        <TestChild />
      </ProjectProvider>
    );

    authMock.currentUser = { uid: "u1" } as any;
    cb(authMock.currentUser);
    await waitFor(() => expect(getByTestId("count").textContent).toBe("1"));
    expect(apiFetchMock).toHaveBeenCalledTimes(1);

    authMock.currentUser = null;
    cb(null);
    await waitFor(() => expect(getByTestId("count").textContent).toBe("0"));
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("sets empty projects when response not ok", async () => {
    onAuthStateChangedMock.mockImplementation((authArg, cb) => {
      authMock.currentUser = { uid: "u1" } as any;
      cb(authMock.currentUser);
      return () => {};
    });
    apiFetchMock.mockResolvedValue({ ok: false, json: async () => ({ detail: "unauthorized" }) });

    const { getByTestId } = render(
      <ProjectProvider>
        <TestChild />
      </ProjectProvider>
    );

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());
    await waitFor(() => expect(getByTestId("count").textContent).toBe("0"));
  });

  it("sets empty projects when JSON is not array", async () => {
    onAuthStateChangedMock.mockImplementation((authArg, cb) => {
      authMock.currentUser = { uid: "u1" } as any;
      cb(authMock.currentUser);
      return () => {};
    });
    apiFetchMock.mockResolvedValue({ ok: true, json: async () => ({ detail: "oops" }) });

    const { getByTestId } = render(
      <ProjectProvider>
        <TestChild />
      </ProjectProvider>
    );

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());
    await waitFor(() => expect(getByTestId("count").textContent).toBe("0"));
  });
});
