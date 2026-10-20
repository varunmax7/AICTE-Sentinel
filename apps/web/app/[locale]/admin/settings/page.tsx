import { ProfileSettings } from "@/components/shell/profile-settings";
import { getServerMe } from "@/lib/api-server";

export default async function AdminSettingsPage() {
  const me = await getServerMe();
  if (!me) return null;
  return <ProfileSettings me={me} />;
}
