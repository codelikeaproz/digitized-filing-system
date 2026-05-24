/**
 * LoginPage — public login form.
 * API: POST /api/auth/login → stores JWT in localStorage via auth-context.
 */
import React, { useState } from 'react'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle,
  CardFooter
} from "@/components/ui/card"
import { Link } from "react-router-dom"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await login(formData.email, formData.password)
      toast.success("Login successful")
      window.location.assign("/")
    } catch (error: any) {
      console.error(error)
    } finally {
      setIsLoading(false)
    }
  }

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
            <img
              src="/img/login_logo.png"
              alt="DigiFile logo"
              className="h-12 w-12 rounded-xl object-contain "
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

      {/* Right Panel - Login Form Section */}
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
                <CardTitle className="text-xl font-bold text-gray-900">Welcome Back</CardTitle>
                <CardDescription className="text-sm text-gray-500 font-medium">
                  Please sign in to access your dashboard
                </CardDescription>
              </div>
            </CardHeader>
            
            <CardContent className="px-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-xs font-bold text-gray-700">Email address</Label>
                  <Input
                    id="email"
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="Enter your email address"
                    required
                    className="rounded-xl h-12 border-gray-100 bg-gray-50/50 focus:bg-white transition-all"
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password" title="password" className="text-xs font-bold text-gray-700">Password</Label>
                    <Link to="/forgot-password" className="text-xs font-bold text-[#0A4D27] hover:underline">Forgot password?</Link>
                  </div>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      value={formData.password}
                      onChange={handleInputChange}
                      placeholder="Enter your password"
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
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <Button 
                  type="submit" 
                  className="w-full bg-[#0A4D27] hover:bg-[#083E1D] text-white rounded-xl py-6 font-bold text-sm h-12 transition-all shadow-lg shadow-[#0A4D27]/10 flex items-center justify-center gap-2 group"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin text-white" />
                      Signing in...
                    </>
                  ) : (
                    "Login"
                  )}
                </Button>
              </form>
            </CardContent>

            <CardFooter className="flex flex-col space-y-6 pt-4 pb-10 px-8">
              <div className="pt-2 flex flex-col items-center gap-4">
                <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                  <span className="w-12 h-[1px] bg-gray-100" />
                  Secured by System
                  <span className="w-12 h-[1px] bg-gray-100" />
                </div>
              </div>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  )
}
