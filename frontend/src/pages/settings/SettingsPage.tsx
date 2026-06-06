/**
 * SettingsPage — profile management and account security.
 *
 * APIs:
 *   GET/PATCH /api/profile/
 *   POST      /api/profile/avatar/
 *   POST      /api/profile/change-password/
 */
import React from "react";
import { Settings as SettingsIcon } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileSettingsForm } from "@/components/settings/ProfileSettingsForm";
import { SecuritySettingsForm } from "@/components/settings/SecuritySettingsForm";
import { SystemSettingsForm } from "@/components/settings/SystemSettingsForm";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-6 w-6 text-primary" />
          <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        </div>
        <p className="text-muted-foreground">Manage your profile information and account security.</p>
      </div>

      <Tabs defaultValue="profile" className="w-full">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          {isAdmin ? <TabsTrigger value="system">System</TabsTrigger> : null}
        </TabsList>
        <TabsContent value="profile" className="mt-4">
          <ProfileSettingsForm />
        </TabsContent>
        <TabsContent value="security" className="mt-4">
          <SecuritySettingsForm />
        </TabsContent>
        {isAdmin ? (
          <TabsContent value="system" className="mt-4">
            <SystemSettingsForm />
          </TabsContent>
        ) : null}
      </Tabs>
    </div>
  );
}
