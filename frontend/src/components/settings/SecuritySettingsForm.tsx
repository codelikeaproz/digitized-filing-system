import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Shield } from "lucide-react";
import { appPath } from "@/lib/app-path";
import { api } from "@/lib/api";
import { clearAuthStorage } from "@/lib/auth-storage";
import { toast } from "sonner";

export function SecuritySettingsForm() {
  const [passwords, setPasswords] = useState({
    current: "",
    new: "",
    confirm: "",
  });
  const [isUpdating, setIsUpdating] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);

  const handleUpdatePassword = async () => {
    setFieldErrors([]);
    if (!passwords.current || !passwords.new || !passwords.confirm) {
      toast.error("Please fill in all password fields.");
      return;
    }
    if (passwords.new !== passwords.confirm) {
      toast.error("New passwords do not match.");
      return;
    }

    setIsUpdating(true);
    try {
      const response = await api.post<{ message: string; errors?: { errors?: string[] } }>(
        "/api/profile/change-password/",
        {
          current_password: passwords.current,
          new_password: passwords.new,
          confirm_password: passwords.confirm,
        }
      );
      toast.success(response.message || "Password updated successfully. Please login again.");
      setPasswords({ current: "", new: "", confirm: "" });
      clearAuthStorage();
      setTimeout(() => {
        window.location.href = appPath("/login");
      }, 800);
    } catch (error: any) {
      toast.error(error.message || "Failed to update password");
      const nestedErrors = error.errors?.errors;
      if (Array.isArray(nestedErrors)) {
        setFieldErrors(nestedErrors.map(String));
      }
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-600" />
          Security
        </CardTitle>
        <CardDescription>Change your password. You will be signed out after a successful update.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2">
          <Label htmlFor="current">Current Password</Label>
          <Input
            id="current"
            type="password"
            autoComplete="current-password"
            value={passwords.current}
            onChange={(e) => setPasswords((prev) => ({ ...prev, current: e.target.value }))}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="new">New Password</Label>
          <Input
            id="new"
            type="password"
            autoComplete="new-password"
            value={passwords.new}
            onChange={(e) => setPasswords((prev) => ({ ...prev, new: e.target.value }))}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="confirm">Confirm New Password</Label>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            value={passwords.confirm}
            onChange={(e) => setPasswords((prev) => ({ ...prev, confirm: e.target.value }))}
          />
        </div>
        {fieldErrors.length > 0 && (
          <ul className="text-xs text-destructive space-y-1 list-disc pl-4">
            {fieldErrors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}
        <Button size="sm" onClick={handleUpdatePassword} disabled={isUpdating}>
          {isUpdating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Update Password
        </Button>
      </CardContent>
    </Card>
  );
}
