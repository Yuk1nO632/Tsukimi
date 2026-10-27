import CalendarBoard from "../../components/calendar-board";
export const metadata = { title: "放送日历" };
export default function CalendarPage() {
  return (
    <div className="content-shell portal-page">
      <div className="portal-heading">
        <div>
          <span className="portal-eyebrow">每周放送</span>
          <h1>放送日历</h1>
          <p>当前在播动画的每周放送安排，按北京时间标记今天。</p>
        </div>
      </div>
      <CalendarBoard />
    </div>
  );
}
