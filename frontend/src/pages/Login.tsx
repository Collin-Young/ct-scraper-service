import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Eye, EyeOff, Lock, Mail, Shield, LogIn } from "lucide-react";
import Nav from "../components/Nav";

export default function LoginPage() {
  const [searchParams] = useSearchParams();
  const showSSO = searchParams.get("sso") === "true";
  interface LoginForm {
    email: string;
    password: string;
  }

  const [tab, setTab] = useState("email");
  const [formData, setFormData] = useState<LoginForm>({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState(""); // idle, loading, success, error
  const [emailForMagic, setEmailForMagic] = useState("");

  const validateEmailPassword = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.email || !/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = "Valid email required";
    if (!formData.password || formData.password.length < 8) newErrors.password = "Password must be at least 8 characters";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateMagicLink = () => {
    if (!emailForMagic || !/\S+@\S+\.\S+/.test(emailForMagic)) {
      setErrors({ email: "Valid email required" });
      return false;
    }
    setErrors({});
    return true;
  };

  const handleEmailPasswordSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateEmailPassword()) return;
    setStatus("loading");
    await new Promise((resolve) => setTimeout(resolve, 1500));
    if (Math.random() > 0.2) {
      setStatus("success");
      // Redirect to dashboard
      window.location.href = "/app";
    } else {
      setStatus("error");
      setErrors({ general: "Invalid credentials. Try again or reset password." });
    }
  };

  const handleMagicLinkSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateMagicLink()) return;
    setStatus("loading");
    await new Promise((resolve) => setTimeout(resolve, 1500));
    if (Math.random() > 0.1) {
      setStatus("success");
      alert("Magic link sent! Check your email.");
    } else {
      setStatus("error");
      setErrors({ general: "Failed to send link. Try again." });
    }
  };

  const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 },
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 flex items-center justify-center py-12 px-4">
      {/* Hero */}
      <Nav />

      <motion.main {...fadeInUp} className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Secure Login</h1>
          <p className="text-zinc-400 mb-4">Access your dashboard quickly and safely.</p>
          <div className="flex justify-center gap-4 text-xs">
            <span className="flex items-center text-zinc-500">
              <Shield className="h-3 w-3 mr-1" aria-hidden="true" /> AES-256 Encryption
            </span>
            <span className="flex items-center text-zinc-500">
              <Shield className="h-3 w-3 mr-1" aria-hidden="true" /> SOC2-Ready
            </span>
          </div>
        </div>

        {showSSO && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-indigo-500/20 border border-indigo-500/30 rounded-lg p-4 mb-6 text-center"
          >
            <p className="text-sm font-medium mb-2">Enterprise SSO Available</p>
            <Button
              asChild
              className="w-full bg-indigo-600 hover:bg-indigo-700"
              onClick={() => window.location.href = "/sso"}
              aria-label="Login with SSO"
            >
              <span>Login with SSO</span>
            </Button>
          </motion.div>
        )}

        <Card className="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
          <CardContent className="p-6 space-y-6">
            <div className="flex border-b border-zinc-700">
              <button
                className={`flex-1 py-3 font-medium transition-colors ${tab === "email" ? "border-b-2 border-indigo-500 text-indigo-400" : "text-zinc-400"}`}
                onClick={() => setTab("email")}
                aria-selected={tab === "email"}
              >
                Email & Password
              </button>
              <button
                className={`flex-1 py-3 font-medium transition-colors ${tab === "magic" ? "border-b-2 border-indigo-500 text-indigo-400" : "text-zinc-400"}`}
                onClick={() => setTab("magic")}
                aria-selected={tab === "magic"}
              >
                Magic Link
              </button>
            </div>

            {tab === "email" && (
              <form onSubmit={handleEmailPasswordSubmit} className="space-y-4">
                {errors.general && (
                  <div role="alert" className="text-sm text-red-400 bg-red-900/20 border border-red-500/30 rounded p-3" aria-live="polite">
                    {errors.general}
                  </div>
                )}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2 sr-only">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" aria-hidden="true" />
                    <input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className={`w-full pl-10 pr-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${errors.email ? "border-red-500" : ""}`}
                      placeholder="your@email.com"
                      required
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? "email-error" : undefined}
                    />
                  </div>
                  {errors.email && <p id="email-error" className="text-sm text-red-400 mt-1">{errors.email}</p>}
                </div>
                <div>
                  <label htmlFor="password" className="block text-sm font-medium mb-2 sr-only">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" aria-hidden="true" />
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className={`w-full pl-10 pr-12 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${errors.password ? "border-red-500" : ""}`}
                      placeholder="Enter your password"
                      required
                      minLength={8}
                      aria-invalid={!!errors.password}
                      aria-describedby={errors.password ? "password-error" : undefined}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.password && <p id="password-error" className="text-sm text-red-400 mt-1">{errors.password}</p>}
                </div>
                <div className="flex items-center justify-between">
                  <label className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-zinc-700 rounded"
                    />
                    <span className="ml-2">Remember me</span>
                  </label>
                  <Link to="/forgot-password" className="text-sm text-indigo-400 hover:underline">Forgot password?</Link>
                </div>
                <Button
                  type="submit"
                  disabled={status === "loading"}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                  aria-label="Login with email and password"
                >
                  {status === "loading" ? "Logging in..." : "Login"}
                </Button>
                <p className="text-xs text-zinc-500 text-center">
                  We never store your password in plain text. Secure by design.
                </p>
              </form>
            )}

            {tab === "magic" && (
              <form onSubmit={handleMagicLinkSubmit} className="space-y-4">
                {errors.general && (
                  <div role="alert" className="text-sm text-red-400 bg-red-900/20 border border-red-500/30 rounded p-3" aria-live="polite">
                    {errors.general}
                  </div>
                )}
                <div>
                  <label htmlFor="magic-email" className="block text-sm font-medium mb-2 sr-only">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" aria-hidden="true" />
                    <input
                      id="magic-email"
                      type="email"
                      value={emailForMagic}
                      onChange={(e) => setEmailForMagic(e.target.value)}
                      className={`w-full pl-10 pr-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${errors.email ? "border-red-500" : ""}`}
                      placeholder="your@email.com"
                      required
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? "magic-email-error" : undefined}
                    />
                  </div>
                  {errors.email && <p id="magic-email-error" className="text-sm text-red-400 mt-1">{errors.email}</p>}
                </div>
                <Button
                  type="submit"
                  disabled={status === "loading"}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                  aria-label="Send magic link"
                >
                  {status === "loading" ? "Sending..." : "Send Magic Link"}
                </Button>
                <p className="text-xs text-zinc-500 text-center">
                  Check your email for a secure login link. Expires in 15 minutes.
                </p>
              </form>
            )}

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-700" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-zinc-950 px-2 text-zinc-500">Or continue with</span>
              </div>
            </div>

            <div className="space-y-3">
              <Button
                type="button"
                variant="outline"
                className="w-full border-zinc-700 hover:bg-zinc-800/50 flex items-center justify-center gap-2"
                onClick={() => window.location.href = "/api/auth/google"}
                aria-label="Login with Google"
              >
                <LogIn className="h-4 w-4" /> Google
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full border-zinc-700 hover:bg-zinc-800/50 flex items-center justify-center gap-2"
                onClick={() => window.location.href = "/api/auth/microsoft"}
                aria-label="Login with Microsoft"
              >
                <LogIn className="h-4 w-4" /> Microsoft
              </Button>
            </div>

            <p className="text-center text-xs text-zinc-500">
              By continuing, you agree to our <Link to="/terms" className="text-indigo-400 hover:underline">Terms of Service</Link> and <Link to="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</Link>.
            </p>

            <div className="text-center space-y-2">
              <Link to="/signup" className="block text-sm text-indigo-400 hover:underline">Don't have an account? Create one</Link>
              <Link to="/contact" className="block text-sm text-zinc-400 hover:underline">Need help? Contact support</Link>
            </div>
          </CardContent>
        </Card>

        <footer className="mt-8 text-center text-xs text-zinc-500 space-y-1">
          <div>
            <Link to="/terms" className="hover:underline">Terms</Link> • <Link to="/privacy" className="hover:underline">Privacy</Link>
          </div>
          <p>&copy; 2024 DocketVista. All rights reserved.</p>
        </footer>
      </motion.main>
    </div>
  );
}