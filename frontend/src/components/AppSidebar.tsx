/**
 * AppSidebar — role-based primary navigation.
 *
 * Menu visibility must stay aligned with RoleRoute guards in App.tsx:
 *   admin     → all items + Administration (Backup Management)
 *   dept_head → Users + Recycle Bin (scoped on backend)
 *   staff     → Dashboard, Documents, Settings only
 */
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar";
import { 
  LayoutDashboard, 
  Files, 
  Archive, 
  History, 
  LogOut,
  Settings,
  Building2,
  Users,
  HardDriveDownload,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";

// Base menu for all roles
const defaultMenuItems = [
  { title: "Dashboard", icon: LayoutDashboard, url: "/" },
  { title: "Documents", icon: Files, url: "/documents" },
  { title: "Settings", icon: Settings, url: "/settings" },
];

// Admin-only menu items
const adminMenuItems = [
  ...defaultMenuItems.slice(0, 2),
  { title: "Office Units", icon: Building2, url: "/org-units" },
  { title: "User Management", icon: Users, url: "/users" },
  { title: "Audit Logs", icon: History, url: "/audit-logs" },
  { title: "Recycle Bin", icon: Archive, url: "/recycle-bin" },
  ...defaultMenuItems.slice(2),
];

const deptHeadMenuItems = [
  ...defaultMenuItems.slice(0, 2),
  { title: "User Management", icon: Users, url: "/users" },
  { title: "Recycle Bin", icon: Archive, url: "/recycle-bin" },
  ...defaultMenuItems.slice(2),
];

const adminBackupItems = [
  { title: "Backup Management", icon: HardDriveDownload, url: "/backup" },
];

export function AppSidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Select items based on user role
  const menuItems = user?.role?.toLowerCase() === "admin" 
    ? adminMenuItems 
    : user?.role?.toLowerCase() === "dept_head"
      ? deptHeadMenuItems
      : defaultMenuItems;
  const isAdmin = user?.role?.toLowerCase() === "admin";

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <img src="/img/login_logo.png" alt="DigiFile logo" />
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-extrabold tracking-tight text-sidebar-foreground">DigiFile</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="pt-[25px] pb-[20px] pr-1 border-t border-white/10">
          <SidebarGroupLabel className="px-4 pt-0 mb-[5px] h-auto">Main Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton 
                    className="h-9 px-4 text-sm font-medium"
                    isActive={location.pathname === item.url}
                    tooltip={item.title}
                    render={<Link to={item.url} />}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {isAdmin && (
          <SidebarGroup className="pt-[10px] pb-[20px] pr-1 border-t border-white/10">
            <SidebarGroupLabel className="px-4 pt-0 mb-[5px] h-auto">Administration</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu className="gap-1">
                {adminBackupItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      className="h-9 px-4 text-sm font-medium"
                      isActive={location.pathname === item.url}
                      tooltip={item.title}
                      render={<Link to={item.url} />}
                    >
                      <item.icon />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter className="p-4 mt-auto border-t border-white/20">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton 
              className="h-9 px-2 text-sm font-medium text-[#FF3333] hover:text-[#FF3333] hover:bg-transparent justify-start"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2 scale-x-[-1]" />
              <span>Logout</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
