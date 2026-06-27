import type { Task } from "../types/task";

interface Props {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
}

export function TaskTaskList({ tasks, onTaskClick }: Props) {
  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "Critical":
        return <span className="bg-red-50 text-red-700 border border-red-100 px-2 py-0.5 rounded text-xs font-semibold">Critical</span>;
      case "High":
        return <span className="bg-orange-50 text-orange-700 border border-orange-100 px-2 py-0.5 rounded text-xs font-semibold">High</span>;
      case "Medium":
        return <span className="bg-yellow-50 text-yellow-700 border border-yellow-100 px-2 py-0.5 rounded text-xs font-semibold">Medium</span>;
      default:
        return <span className="bg-slate-50 text-slate-700 border border-slate-100 px-2 py-0.5 rounded text-xs font-semibold">Low</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Todo":
        return <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">Todo</span>;
      case "In Progress":
        return <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">In Progress</span>;
      case "Review":
        return <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">In Review</span>;
      case "Blocked":
        return <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">Blocked</span>;
      case "Done":
        return <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">Done</span>;
      default:
        return <span className="bg-slate-50 text-slate-600 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">{status}</span>;
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-12 text-center text-slate-400">
        <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        Tidak ada task
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 text-slate-400 text-xs font-bold uppercase tracking-wider border-b border-slate-100">
              <th className="py-3 px-6">ID</th>
              <th className="py-3 px-6">Summary / Title</th>
              <th className="py-3 px-6">Assignee</th>
              <th className="py-3 px-6">Reporter</th>
              <th className="py-3 px-6">Priority</th>
              <th className="py-3 px-6 font-medium">Status</th>
              <th className="py-3 px-6 text-center">SP</th>
              <th className="py-3 px-6">Due Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700 text-sm">
            {tasks.map((task) => (
              <tr
                key={task.id}
                onClick={() => onTaskClick(task)}
                className="hover:bg-slate-50/50 cursor-pointer transition-colors"
              >
                <td className="py-4 px-6 font-semibold text-blue-600 whitespace-nowrap">
                  WDD-{task.id}
                </td>
                <td className="py-4 px-6 font-medium text-slate-800">
                  {task.title}
                </td>
                <td className="py-4 px-6 whitespace-nowrap">
                  👤 {task.assignee}
                </td>
                <td className="py-4 px-6 whitespace-nowrap text-slate-500">
                  {task.created_by}
                </td>
                <td className="py-4 px-6 whitespace-nowrap">
                  {getPriorityBadge(task.priority)}
                </td>
                <td className="py-4 px-6 whitespace-nowrap">
                  {getStatusBadge(task.status)}
                </td>
                <td className="py-4 px-6 text-center font-bold text-slate-600">
                  {task.story_points}
                </td>
                <td className="py-4 px-6 whitespace-nowrap text-slate-500">
                  {new Date(task.due_date).toLocaleDateString("id-ID", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
