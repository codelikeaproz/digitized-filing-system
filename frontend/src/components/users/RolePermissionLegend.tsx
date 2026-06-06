import { ShieldAlert, ShieldCheck, UserRound } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ROLE_ITEMS = [
  {
    role: "Admin",
    icon: ShieldAlert,
    color: "text-purple-700",
    description: "Full system access, Office Unit management, audit logs, and global user administration.",
  },
  {
    role: "Head",
    icon: ShieldCheck,
    color: "text-blue-700",
    description: "Manages Staff within assigned Office Unit subtree, recycle bin access, and document deletion.",
  },
  {
    role: "Staff",
    icon: UserRound,
    color: "text-emerald-700",
    description: "Uploads and manages documents within assigned Office Unit. Cannot delete documents.",
  },
];

export function RolePermissionLegend() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Role Permission Legend</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-3">
        {ROLE_ITEMS.map((item) => (
          <div key={item.role} className="rounded-xl border p-4 space-y-2">
            <div className={`flex items-center gap-2 font-semibold ${item.color}`}>
              <item.icon className="h-4 w-4" />
              {item.role}
            </div>
            <p className="text-sm text-muted-foreground">{item.description}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
