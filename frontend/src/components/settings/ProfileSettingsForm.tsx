import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Loader2, Upload, UserRound } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";

const SUFFIX_OPTIONS = [
  { value: "", label: "No Suffix" },
  { value: "Jr.", label: "Jr." },
  { value: "Sr.", label: "Sr." },
  { value: "I", label: "I" },
  { value: "II", label: "II" },
  { value: "III", label: "III" },
  { value: "IV", label: "IV" },
  { value: "V", label: "V" },
] as const;

export type ProfileData = {
  id: string;
  email: string;
  role: string;
  firstName?: string;
  lastName?: string;
  suffix?: string;
  employeeNumber?: string;
  orgUnitName?: string;
  fullName?: string;
  profilePictureUrl?: string | null;
};

function roleLabel(role?: string) {
  switch (role?.toLowerCase()) {
    case "admin":
      return "Admin";
    case "dept_head":
      return "Head";
    case "staff":
      return "Staff";
    default:
      return role || "—";
  }
}

function initialsFromName(name?: string) {
  if (!name) return "U";
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png"];
const MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024;

export function ProfileSettingsForm() {
  const { rehydrate } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    suffix: "",
  });
  const [pendingAvatar, setPendingAvatar] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const suffixOptions = useMemo((): { value: string; label: string }[] => {
    const options: { value: string; label: string }[] = SUFFIX_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label,
    }));
    const current = formData.suffix;
    if (current && !options.some((option) => option.value === current)) {
      options.push({ value: current, label: current });
    }
    return options;
  }, [formData.suffix]);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const data = await api.get<ProfileData>("/api/profile/");
      setProfile(data);
      setFormData({
        firstName: data.firstName || "",
        lastName: data.lastName || "",
        suffix: data.suffix || "",
      });
      setPreviewUrl(data.profilePictureUrl || null);
      setPendingAvatar(null);
      setFieldErrors({});
    } catch (error: any) {
      toast.error(error.message || "Failed to load profile");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleAvatarSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      toast.error("Upload a JPEG or PNG image.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      toast.error("Image must be 2 MB or smaller.");
      event.target.value = "";
      return;
    }

    if (previewUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrl);
    }
    setPendingAvatar(file);
    setPreviewUrl(URL.createObjectURL(file));
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next.avatar;
      return next;
    });
  };

  const applyValidationErrors = (errors: Record<string, unknown>) => {
    const next: Record<string, string> = {};
    Object.entries(errors).forEach(([key, value]) => {
      if (Array.isArray(value) && value.length) {
        next[key] = String(value[0]);
      } else if (typeof value === "string") {
        next[key] = value;
      }
    });
    setFieldErrors(next);
  };

  const hasProfileChanges =
    profile &&
    (formData.firstName !== (profile.firstName || "") ||
      formData.lastName !== (profile.lastName || "") ||
      formData.suffix !== (profile.suffix || ""));

  const handleSave = async () => {
    if (!profile) return;
    if (!hasProfileChanges && !pendingAvatar) {
      toast.info("No changes to save.");
      return;
    }

    setIsSaving(true);
    setFieldErrors({});
    try {
      let latestProfile = profile;

      if (pendingAvatar) {
        const form = new FormData();
        form.append("avatar", pendingAvatar);
        latestProfile = await api.upload<ProfileData>("/api/profile/avatar/", form);
        setPendingAvatar(null);
      }

      if (hasProfileChanges) {
        latestProfile = await api.patch<ProfileData>("/api/profile/", {
          firstName: formData.firstName.trim(),
          lastName: formData.lastName.trim(),
          suffix: formData.suffix,
        });
      }

      setProfile(latestProfile);
      setFormData({
        firstName: latestProfile.firstName || "",
        lastName: latestProfile.lastName || "",
        suffix: latestProfile.suffix || "",
      });
      setPreviewUrl(latestProfile.profilePictureUrl || null);
      await rehydrate();
      toast.success("Profile updated successfully.");
    } catch (error: any) {
      const message = error.message || "Failed to save profile";
      toast.error(message);
      if (error.errors) {
        applyValidationErrors(error.errors);
      }
    } finally {
      setIsSaving(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const displayName = profile?.fullName || `${formData.firstName} ${formData.lastName}`.trim();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRound className="h-5 w-5 text-[#00491E]" />
          Profile
        </CardTitle>
        <CardDescription>Update your personal information and profile photo.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <Avatar className="h-20 w-20 border border-border">
            {previewUrl ? <AvatarImage src={previewUrl} alt={displayName || "Profile photo"} /> : null}
            <AvatarFallback className="bg-primary/10 text-primary text-lg font-bold">
              {initialsFromName(displayName)}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,.jpg,.jpeg,.png"
              className="hidden"
              aria-label="Profile photo upload"
              onChange={handleAvatarSelect}
            />
            <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
              <Upload className="h-4 w-4 mr-2" />
              Choose Photo
            </Button>
            <p className="text-xs text-muted-foreground">JPEG or PNG only. Max 2 MB.</p>
            {fieldErrors.avatar && <p className="text-xs text-destructive">{fieldErrors.avatar}</p>}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="employeeNumber">Employee Number</Label>
            <Input id="employeeNumber" value={profile?.employeeNumber || "—"} readOnly disabled />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={profile?.email || ""} readOnly disabled />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              value={formData.firstName}
              onChange={(e) => setFormData((prev) => ({ ...prev, firstName: e.target.value }))}
            />
            {fieldErrors.firstName && <p className="text-xs text-destructive">{fieldErrors.firstName}</p>}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              value={formData.lastName}
              onChange={(e) => setFormData((prev) => ({ ...prev, lastName: e.target.value }))}
            />
            {fieldErrors.lastName && <p className="text-xs text-destructive">{fieldErrors.lastName}</p>}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="suffix">Suffix</Label>
            <select
              id="suffix"
              value={formData.suffix}
              aria-label="Name suffix"
              onChange={(e) => setFormData((prev) => ({ ...prev, suffix: e.target.value }))}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {suffixOptions.map((option) => (
                <option key={option.value || "none"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {fieldErrors.suffix && <p className="text-xs text-destructive">{fieldErrors.suffix}</p>}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="role">Role</Label>
            <Input id="role" value={roleLabel(profile?.role)} readOnly disabled />
          </div>
          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="officeUnit">Office Unit</Label>
            <Input id="officeUnit" value={profile?.orgUnitName || "Global Access"} readOnly disabled />
          </div>
        </div>

        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Save Changes
        </Button>
      </CardContent>
    </Card>
  );
}
