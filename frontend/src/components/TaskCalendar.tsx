import { useState } from "react";
import type { Task } from "../types/task";

interface Props {
  readonly tasks: readonly Task[];
  readonly onTaskClick: (task: Task) => void;
}

export function TaskCalendar({ tasks, onTaskClick }: Props) {
  const [currentDate, setCurrentDate] = useState(new Date(2026, 5, 1)); // Default starting month to June 2026

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Get the first day of the month
  const firstDayOfMonth = new Date(year, month, 1);
  // Get day of the week for the first day (0 = Sunday, 1 = Monday, etc.)
  // We want Monday as index 0, so: (day + 6) % 7
  const startDayOffset = (firstDayOfMonth.getDay() + 6) % 7;

  // Get total days in the current month
  const totalDays = new Date(year, month + 1, 0).getDate();

  // Get total days in the previous month
  const prevMonthTotalDays = new Date(year, month, 0).getDate();

  const days: { date: Date; isCurrentMonth: boolean; key: string }[] = [];

  // Padding days from previous month
  for (let i = startDayOffset - 1; i >= 0; i--) {
    days.push({
      date: new Date(year, month - 1, prevMonthTotalDays - i),
      isCurrentMonth: false,
      key: `prev-${prevMonthTotalDays - i}`,
    });
  }

  // Days of the current month
  for (let i = 1; i <= totalDays; i++) {
    days.push({
      date: new Date(year, month, i),
      isCurrentMonth: true,
      key: `curr-${i}`,
    });
  }

  // Padding days from next month to fill grid (usually 42 days total)
  const remainingCells = 42 - days.length;
  for (let i = 1; i <= remainingCells; i++) {
    days.push({
      date: new Date(year, month + 1, i),
      isCurrentMonth: false,
      key: `next-${i}`,
    });
  }

  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const getTasksForDate = (date: Date) => {
    const dateStr = date.toISOString().split("T")[0];
    return tasks.filter((t) => t.due_date === dateStr);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "Critical":
        return "bg-red-50 text-red-700 border-red-100 hover:bg-red-100";
      case "High":
        return "bg-orange-50 text-orange-700 border-orange-100 hover:bg-orange-100";
      case "Medium":
        return "bg-yellow-50 text-yellow-700 border-yellow-100 hover:bg-yellow-100";
      default:
        return "bg-slate-50 text-slate-700 border-slate-100 hover:bg-slate-100";
    }
  };

  const monthNames = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden flex flex-col h-[700px]">
      {/* Calendar Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          📅 {monthNames[month]} {year}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevMonth}
            className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={() => setCurrentDate(new Date(2026, 5, 1))}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Hari Ini
          </button>
          <button
            onClick={handleNextMonth}
            className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Weekdays Label */}
      <div className="grid grid-cols-7 border-b border-slate-100 bg-slate-50/30 text-center text-xs font-bold text-slate-400 uppercase tracking-wider py-2">
        <div>Senin</div>
        <div>Selasa</div>
        <div>Rabu</div>
        <div>Kamis</div>
        <div>Jumat</div>
        <div>Sabtu</div>
        <div>Minggu</div>
      </div>

      {/* Days Grid */}
      <div className="grid grid-cols-7 flex-1 bg-slate-50/50">
        {days.map((day) => {
          const dateTasks = getTasksForDate(day.date);
          return (
            <div
              key={day.key}
              className={`border-r border-b border-slate-100 p-2 flex flex-col gap-1 min-h-[100px] overflow-hidden ${
                day.isCurrentMonth ? "bg-white" : "bg-slate-50/30 opacity-60"
              }`}
            >
              <div className="flex justify-between items-center mb-1">
                <span
                  className={`text-xs font-semibold rounded-full w-5 h-5 flex items-center justify-center ${
                    day.date.toDateString() === new Date().toDateString()
                      ? "bg-blue-600 text-white"
                      : "text-slate-600"
                  }`}
                >
                  {day.date.getDate()}
                </span>
                {dateTasks.length > 0 && (
                  <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full font-bold">
                    {dateTasks.length} task
                  </span>
                )}
              </div>

              <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                {dateTasks.map((t) => (
                  <div
                    key={t.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => onTaskClick(t)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onTaskClick(t);
                      }
                    }}
                    className={`text-[10px] font-semibold border px-1.5 py-1 rounded cursor-pointer transition-colors truncate ${getPriorityColor(
                      t.priority
                    )}`}
                    title={`[WDD-${t.id}] ${t.title}`}
                  >
                    WDD-{t.id}: {t.title}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
