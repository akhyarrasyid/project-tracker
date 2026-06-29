import { RouterProvider } from "react-router-dom";
import { useMemo } from "react";

import { createAppRouter } from "./app/router";
import { AppProviders } from "./app/providers";

export default function App() {
  const router = useMemo(() => createAppRouter(), []);

  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
