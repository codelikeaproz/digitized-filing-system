import type { ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";
import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { publicAsset } from "@/lib/app-path";

export function AuthSystemIntroduction() {
  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-6xl font-bold leading-tight tracking-tight text-white uppercase sm:normal-case">
        Digitized Filing System.
      </h1>
      <p className="text-xl text-white font-medium leading-relaxed">
        The official document management system of
        <br />
        <span className="whitespace-nowrap">Central Mindanao University</span>
      </p>
    </div>
  );
}

export function AuthCardHeader({ title, description }: { title: string; description: string }) {
  return (
    <CardHeader className="space-y-4 py-8 flex flex-col items-center text-center">
      <div className="flex items-center">
        <div className="h-12 w-12 rounded-xl object-contain">
          <img src={publicAsset("img/login_logo.png")} alt="DigiFile logo" />
        </div>
        <span className="text-2xl font-black tracking-tighter text-gray-900">DigiFile</span>
      </div>
      <div className="space-y-1">
        <CardTitle className="text-xl font-bold text-gray-900">{title}</CardTitle>
        <CardDescription className="text-sm text-gray-500 font-medium">{description}</CardDescription>
      </div>
    </CardHeader>
  );
}

export function AuthSuccessMessage({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action: ReactNode;
}) {
  return (
    <div className="py-6 flex flex-col items-center justify-center space-y-4 text-center animate-in fade-in zoom-in">
      <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
        <CheckCircle2 className="h-8 w-8 text-green-600" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
      <p className="text-sm text-gray-500 max-w-sm">{children}</p>
      {action}
    </div>
  );
}
