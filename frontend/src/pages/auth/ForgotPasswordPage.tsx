// Forgot password page for requesting a reset link.
import React, { useState } from 'react';
import { ArrowLeft, Building2, Loader2, CheckCircle2 } from 'lucide-react';
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle,
  CardFooter
} from "@/components/ui/card";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    try {
      const response = await api.requestPasswordReset(email);
      setIsSuccess(true);
      toast.success(response.message || "Reset link sent if the account exists");
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "Failed to request password reset");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-white font-sans overflow-hidden">
      {/* Left Panel - Branding Section with Image Background */}
      <div className="hidden lg:flex flex-1 relative text-white p-16 flex-col justify-between overflow-hidden">
        <div className="absolute inset-0 z-0">
        <img
            src="/img/login_hero.jpeg"
            alt="Office Desk"
            className="w-full h-full object-cover"
            referrerPolicy="no-referrer"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/img/login_hero.jpeg'
            }}
          />
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" />
        </div>

        <div className="z-20">
          <div className="flex items-center *:mb-12">
            <img
              src="/img/login_logo.png"
              alt="DigiFile logo"
              className="h-12 w-12 rounded-xl object-contain"
            />
            <span className="text-xl font-bold tracking-tighter">DigiFile</span>
          </div>
        </div>

        <div className="z-20 flex flex-col items-start justify-center flex-1 text-left">
          <div className="max-w-xl space-y-6">
            <h1 className="text-6xl font-bold leading-tight tracking-tight text-white uppercase sm:normal-case">
              Digitized Filing System.
            </h1>
            <p className="text-xl text-white font-medium leading-relaxed">
              The Official Document Management System of the Office of the 
              Vice-President for Academic Affairs
            </p>
          </div>
        </div>

        <div className="z-20 flex flex-col gap-4">
          <p className="text-sm text-gray-400 font-medium">@2026 Digifile</p>
        </div>
      </div>

      {/* Right Panel - Form Section */}
      <div className="flex-1 flex items-center justify-center p-8 bg-gray-50/50 relative">
        <div className="w-full max-w-[520px] space-y-8">
          <Card className="shadow-[0_8px_30px_rgb(0,0,0,0.04)] border-none rounded-2xl bg-white p-2">
            <CardHeader className="space-y-4 py-8 flex flex-col items-center text-center">
              <div className="flex items-center">
                <div className="h-12 w-12 rounded-xl object-contain">
                  <img src="/img/login_logo.png" alt="DigiFile logo" />
                </div>
                <span className="text-2xl font-black tracking-tighter text-gray-900">DigiFile</span>
              </div>
              <div className="space-y-1">
                <CardTitle className="text-xl font-bold text-gray-900">Reset Password</CardTitle>
                <CardDescription className="text-sm text-gray-500 font-medium">
                  Enter your email to receive a password reset link
                </CardDescription>
              </div>
            </CardHeader>
            
            <CardContent className="px-8">
              {isSuccess ? (
                <div className="py-6 flex flex-col items-center justify-center space-y-4 text-center animate-in fade-in zoom-in">
                  <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900">Link Sent!</h3>
                  <p className="text-sm text-gray-500 max-w-sm">
                    If an account exists for <span className="font-semibold text-gray-900">{email}</span>, a reset link has been sent. Please check your inbox.
                  </p>
                  <Link 
                    to="/login"
                    className={cn(
                      buttonVariants({ variant: "outline" }),
                      "mt-6 w-full flex items-center justify-center rounded-xl py-6 font-bold text-sm h-12"
                    )}
                  >
                    Return to Login
                  </Link>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-xs font-bold text-gray-700">Email address</Label>
                    <Input
                      id="email"
                      type="email"
                      name="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter your email address"
                      required
                      className="rounded-xl h-12 border-gray-100 bg-gray-50/50 focus:bg-white transition-all"
                      disabled={isLoading}
                    />
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full bg-[#0A4D27] hover:bg-[#083E1D] text-white rounded-xl py-6 font-bold text-sm h-12 transition-all shadow-lg shadow-[#0A4D27]/10 flex items-center justify-center gap-2"
                    disabled={isLoading || !email}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin text-white" />
                        Sending Link...
                      </>
                    ) : (
                      "Send Reset Link"
                    )}
                  </Button>
                </form>
              )}
            </CardContent>

            {!isSuccess && (
              <CardFooter className="flex flex-col space-y-6 pt-4 pb-10 px-8">
                <div className="flex items-center justify-center text-xs text-gray-500 font-medium">
                  Remembered your password? 
                  <Link to="/login" className="ml-1 text-[#0A4D27] font-bold hover:underline flex items-center gap-1">
                    <ArrowLeft className="h-3 w-3" /> Back to Sign in
                  </Link>
                </div>

                <div className="pt-2 flex flex-col items-center gap-4">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <span className="w-12 h-[1px] bg-gray-100" />
                    Secured by System
                    <span className="w-12 h-[1px] bg-gray-100" />
                  </div>
                </div>
              </CardFooter>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
