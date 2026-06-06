/**
 * AppShell — authenticated layout wrapper with sidebar and outlet for pages.
 *
 * Rendered inside ProtectedRoute; child routes render via <Outlet />.
 */
import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuth } from "@/lib/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export default function AppShell() {
  const { user } = useAuth();
  
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background font-sans">
        <AppSidebar />
        <main className="flex-1 overflow-auto">
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground sm:hidden">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-building-2 h-5 w-5"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <NotificationBell />
              <div className="h-8 w-[1px] bg-border mx-2"></div>
              
              <div className="flex items-center gap-3">
                <div className="flex flex-col items-end">
                  <span className="text-sm font-bold text-foreground">{user?.fullName}</span>
                  <span className="text-[10px] text-muted-foreground font-medium uppercase">{user?.role?.replace(/_/g, ' ')}</span>
                </div>
                <Avatar className="h-10 w-10 border border-border">
                  {user?.profilePictureUrl ? (
                    <AvatarImage src={user.profilePictureUrl} alt={user.fullName || "Profile photo"} />
                  ) : null}
                  <AvatarFallback className="bg-primary/10 text-primary font-bold">
                    {user?.fullName?.split(" ").map(n => n[0]).join("") || "U"}
                  </AvatarFallback>
                </Avatar>
              </div>
            </div>
          </header>
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}
