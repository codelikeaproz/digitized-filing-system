import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Settings as SettingsIcon, Shield, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function SettingsPage() {
  const [passwords, setPasswords] = useState({
    current: "",
    new: "",
    confirm: ""
  });
  const [isUpdating, setIsUpdating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(false);
  }, []);

  const handleUpdatePassword = async () => {
    // ... same as before
    if (!passwords.current || !passwords.new) {
      toast.error("Please fill in all password fields");
      return;
    }
    if (passwords.new !== passwords.confirm) {
      toast.error("New passwords do not match");
      return;
    }

    setIsUpdating(true);
    try {
      const response = await api.post<{ message: string }>("/api/auth/update-password/", {
        current_password: passwords.current,
        new_password: passwords.new,
        confirm_password: passwords.confirm
      });
      toast.success(response.message || "Password updated successfully. Please login again.");
      setPasswords({ current: "", new: "", confirm: "" });
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      setTimeout(() => {
        window.location.href = "/login";
      }, 800);
    } catch (error: any) {
      toast.error(error.message || "Failed to update password");
    } finally {
      setIsUpdating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ... header ... */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-6 w-6 text-primary" />
          <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        </div>
        <p className="text-muted-foreground">Manage your account security and personal preferences.</p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-600" />
              Security Settings
            </CardTitle>
            <CardDescription>Manage your password and session preferences.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="current">Current Password</Label>
              <Input 
                id="current" 
                type="password" 
                value={passwords.current}
                onChange={(e) => setPasswords({...passwords, current: e.target.value})}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="new">New Password</Label>
              <Input 
                id="new" 
                type="password" 
                value={passwords.new}
                onChange={(e) => setPasswords({...passwords, new: e.target.value})}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="confirm">Confirm New Password</Label>
              <Input 
                id="confirm" 
                type="password" 
                value={passwords.confirm}
                onChange={(e) => setPasswords({...passwords, confirm: e.target.value})}
              />
            </div>
            <Button 
              size="sm" 
              onClick={handleUpdatePassword} 
              disabled={isUpdating}
            >
              {isUpdating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Update Password
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
