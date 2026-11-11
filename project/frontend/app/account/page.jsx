import ContinueWatching from "../../components/continue-watching";
import AccountPanel from "../../components/account-panel";
export const metadata = { title: "我的账号" };
export default function AccountPage() {
  return <>
    <AccountPanel />
    <div className="content-shell account-history"><ContinueWatching manage history /></div>
  </>;
}
