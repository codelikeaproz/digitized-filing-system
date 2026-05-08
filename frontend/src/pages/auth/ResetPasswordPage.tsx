// Reset password page for setting a new password from a reset link.
import React, { useState } from 'react';
import { Building2, Loader2, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle,
  CardFooter
} from "@/components/ui/card";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";

export default function ResetPasswordPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Simple password strength calculation
  const calculateStrength = (pass: string) => {
    let score = 0;
    if (!pass) return 0;
    if (pass.length > 8) score += 25;
    if (pass.match(/[a-z]/) && pass.match(/[A-Z]/)) score += 25;
    if (pass.match(/\d/)) score += 25;
    if (pass.match(/[^a-zA-Z\d]/)) score += 25;
    return score;
  };

  const strength = calculateStrength(password);
  
  const getStrengthIndicator = () => {
    if (strength === 0) return { color: 'bg-gray-200', label: '' };
    if (strength <= 25) return { color: 'bg-red-500', label: 'Weak' };
    if (strength <= 50) return { color: 'bg-orange-500', label: 'Fair' };
    if (strength <= 75) return { color: 'bg-yellow-500', label: 'Good' };
    return { color: 'bg-green-500', label: 'Strong' };
  };

  const strengthData = getStrengthIndicator();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    if (strength < 50) {
      toast.error("Please choose a stronger password.");
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.resetPassword({ uid, token, new_password: password, confirm_password: confirmPassword });
      setIsSuccess(true);
      toast.success(response.message || "Password has been reset successfully.");
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "Failed to reset password. The link might be expired.");
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
          <div className="flex items-center mb-12">
            <div className="h-12 w-12 rounded-xl object-contain">
              <img src="/img/login_logo.png" alt="DigiFile logo" />
            </div>
            <span className="text-xl font-bold tracking-tight">DigiFile</span>
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
                <CardTitle className="text-xl font-bold text-gray-900">Set New Password</CardTitle>
                <CardDescription className="text-sm text-gray-500 font-medium">
                  Please enter your new password below.
                </CardDescription>
              </div>
            </CardHeader>
            
            <CardContent className="px-8">
              {isSuccess ? (
                <div className="py-6 flex flex-col items-center justify-center space-y-4 text-center animate-in fade-in zoom-in">
                  <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900">Password Reset Complete</h3>
                  <p className="text-sm text-gray-500 max-w-sm">
                    Your password has been reset successfully. You can now log in using your new credentials.
                  </p>
                  <Button 
                    onClick={() => navigate('/login')}
                    className="mt-6 w-full bg-[#0A4D27] hover:bg-[#083E1D] text-white rounded-xl py-6 font-bold text-sm h-12 shadow-lg shadow-[#0A4D27]/10"
                  >
                    Go to Login
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="password" title="password" className="text-xs font-bold text-gray-700">New Password</Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter new password"
                        required
                        className="pr-12 rounded-xl h-12 border-gray-100 bg-gray-50/50 focus:bg-white transition-all"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none transition-colors"
                        disabled={isLoading}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {password && (
                      <div className="pt-2 space-y-1">
                        <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-gray-500">
                          <span>Password Strength</span>
                          <span className={strengthData.color.replace('bg-', 'text-')}>{strengthData.label}</span>
                        </div>
                        <Progress value={strength} indicatorClassName={strengthData.color} className="h-1.5" />
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm_password" title="confirm password" className="text-xs font-bold text-gray-700">Confirm Password</Label>
                    <div className="relative">
                      <Input
                        id="confirm_password"
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Confirm new password"
                        required
                        className="pr-12 rounded-xl h-12 border-gray-100 bg-gray-50/50 focus:bg-white transition-all"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none transition-colors"
                        disabled={isLoading}
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {confirmPassword && password !== confirmPassword && (
                      <p className="text-xs text-red-500 font-medium pt-1">Passwords do not match</p>
                    )}
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full bg-[#0A4D27] hover:bg-[#083E1D] text-white rounded-xl py-6 mt-4 font-bold text-sm h-12 transition-all shadow-lg shadow-[#0A4D27]/10 flex items-center justify-center gap-2"
                    disabled={isLoading || !password || password !== confirmPassword || strength < 50}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin text-white" />
                        Resetting...
                      </>
                    ) : (
                      "Reset Password"
                    )}
                  </Button>
                </form>
              )}
            </CardContent>

            {!isSuccess && (
              <CardFooter className="flex flex-col space-y-6 pt-4 pb-10 px-8">
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
