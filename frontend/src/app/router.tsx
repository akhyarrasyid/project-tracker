import { Navigate, createBrowserRouter } from "react-router-dom";

import { WorkspaceLayout } from "../layouts/WorkspaceLayout";
import { ProjectLayout } from "../layouts/ProjectLayout";
import { CalendarPage } from "../routes/CalendarPage";
import { IssuePage } from "../routes/IssuePage";
import { IssuesPage } from "../routes/IssuesPage";
import { MyIssuesPage } from "../routes/MyIssuesPage";
import { ProjectBoardPage } from "../routes/ProjectBoardPage";

export function createAppRouter() {
  return createBrowserRouter([
    {
      path: "/",
      element: <WorkspaceLayout />,
      children: [
        { index: true, element: <Navigate to="/my-issues" replace /> },
        { path: "my-issues", element: <MyIssuesPage /> },
        { path: "issues/:issueKey", element: <IssuePage /> },
        {
          path: "projects/:projectKey",
          element: <ProjectLayout />,
          children: [
            { index: true, element: <Navigate to="board" replace /> },
            { path: "board", element: <ProjectBoardPage /> },
            { path: "issues", element: <IssuesPage /> },
            { path: "calendar", element: <CalendarPage /> },
          ],
        },
      ],
    },
  ]);
}
