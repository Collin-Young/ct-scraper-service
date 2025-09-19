import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import Nav from "../components/Nav";
import { Mail, Phone, Clock, MapPin, User, MailOpen, FileText, Shield, Users, Zap } from "lucide-react";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    role: "",
    plan: "",
    message: "",
    honeypot: "",
    consent: false,
    file: null as File | null,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState(""); // idle, loading, success, error
  const [submitted, setSubmitted] = useState(false);

  const roles = ["Investor", "Agent", "Attorney", "Other"];
  const plans = ["Basic", "Pro", "Enterprise", "Not Sure"];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.email.trim() || !/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = "Valid email is required";
    if (!formData.company.trim()) newErrors.company = "Company is required";
    if (!formData.role) newErrors.role = "Role is required";
    if (!formData.plan) newErrors.plan = "Plan is required";
    if (formData.message.length < 20) newErrors.message = "Message must be at least 20 characters";
    if (!formData.consent) newErrors.consent = "You must consent to proceed";
    if (formData.honeypot) newErrors.honeypot = "Invalid submission";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateForm()) return;
    setStatus("loading");
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    if (Math.random() > 0.1) { // 90% success
      setStatus("success");
      setSubmitted(true);
    } else {
      setStatus("error");
      // Fallback to mailto
      const subject = `Contact from ${formData.name} - ${formData.role}`;
      const body = `Email: ${formData.email}\nCompany: ${formData.company}\nRole: ${formData.role}\nPlan: ${formData.plan}\nMessage: ${formData.message}`;
      window.location.href = `mailto:support@docketvista.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }
  };

  const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true },
  };

  if (submitted && status === "success") {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-200">
        <Nav />
        <motion.section {...fadeInUp} className="py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-bold mb-4">Thanks for Reaching Out!</h1>
          <p className="text-xl text-zinc-400 mb-8">We'll respond within 2 business hours. In the meantime, explore our dashboard.</p>
          <Button asChild size="lg" className="bg-indigo-600 hover:bg-indigo-700">
            <Link to="/app">Go to Dashboard</Link>
          </Button>
        </motion.section>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <Nav />

      {/* Hero */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeInUp} className="text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">Get Support or Book a Demo – We're Here for Your Success</h1>
          <p className="text-xl text-zinc-400 mb-8">Book a 15-min demo to see AI leads in action, or contact for billing, leads, expansion. SLA: Email Response 24 Hours | Phone M-F 9-5 EST.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <Button asChild size="lg" className="bg-[#5227FF] hover:bg-[#4F20E8] px-8">
              <a href="https://calendly.com/docketvista/demo" target="_blank" rel="noopener noreferrer">Book 15-Min Demo</a>
            </Button>
            <Button variant="outline" asChild size="lg" className="border-white/20 text-white hover:bg-white/10 px-8">
              <Link to="/pricing">View Plans</Link>
            </Button>
          </div>
          <p className="text-sm text-zinc-500 text-center">Categories: Billing | Leads | Expansion Queries</p>
        </motion.div>
      </section>

      {/* Contact Form & Cards */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Form */}
          <motion.form {...fadeInUp} onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="honeypot" className="sr-only">Leave blank</label>
              <input
                type="text"
                id="honeypot"
                value={formData.honeypot}
                onChange={(e) => setFormData({ ...formData, honeypot: e.target.value })}
                className="sr-only"
              />
            </div>
            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-2">Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.name ? 'border-red-500' : ''}`}
                aria-describedby={errors.name ? "name-error" : undefined}
                required
              />
              {errors.name && <p id="name-error" className="text-sm text-red-500 mt-1">{errors.name}</p>}
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">Work Email <span className="text-red-500">*</span></label>
              <input
                type="email"
                id="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.email ? 'border-red-500' : ''}`}
                aria-describedby={errors.email ? "email-error" : undefined}
                required
              />
              {errors.email && <p id="email-error" className="text-sm text-red-500 mt-1">{errors.email}</p>}
            </div>
            <div>
              <label htmlFor="company" className="block text-sm font-medium mb-2">Company <span className="text-red-500">*</span></label>
              <input
                type="text"
                id="company"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.company ? 'border-red-500' : ''}`}
                aria-describedby={errors.company ? "company-error" : undefined}
                required
              />
              {errors.company && <p id="company-error" className="text-sm text-red-500 mt-1">{errors.company}</p>}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="role" className="block text-sm font-medium mb-2">Role <span className="text-red-500">*</span></label>
                <select
                  id="role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.role ? 'border-red-500' : ''}`}
                  aria-describedby={errors.role ? "role-error" : undefined}
                  required
                >
                  <option value="">Select...</option>
                  {roles.map((role) => <option key={role} value={role}>{role}</option>)}
                </select>
                {errors.role && <p id="role-error" className="text-sm text-red-500 mt-1">{errors.role}</p>}
              </div>
              <div>
                <label htmlFor="category" className="block text-sm font-medium mb-2">Support Category <span className="text-red-500">*</span></label>
                <select
                  id="category"
                  value={formData.plan} // Reuse plan state for category
                  onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                  className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.plan ? 'border-red-500' : ''}`}
                  aria-describedby={errors.plan ? "plan-error" : undefined}
                  required
                >
                  <option value="">Choose one</option>
                  <option value="billing">Billing & Subscriptions</option>
                  <option value="leads">Leads & Data Questions</option>
                  <option value="expansion">Expansion Interest</option>
                  <option value="technical">Technical Support</option>
                  <option value="general">General Inquiry</option>
                </select>
                {errors.plan && <p id="plan-error" className="text-sm text-red-500 mt-1">{errors.plan}</p>}
              </div>
            </div>
            <div>
              <label htmlFor="message" className="block text-sm font-medium mb-2">Message <span className="text-red-500">*</span></label>
              <textarea
                id="message"
                rows={4}
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                className={`w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${errors.message ? 'border-red-500' : ''}`}
                aria-describedby={errors.message ? "message-error" : undefined}
                placeholder="Tell us how we can help—deals, features, or custom needs."
                required
              />
              {errors.message && <p id="message-error" className="text-sm text-red-500 mt-1">{errors.message}</p>}
            </div>
            <div>
              <label htmlFor="file" className="block text-sm font-medium mb-2">Attachment (Optional)</label>
              <input
                type="file"
                id="file"
                onChange={(e) => setFormData({ ...formData, file: e.target.files?.[0] || null })}
                className="w-full px-3 py-2 border border-zinc-600 rounded-lg bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700"
              />
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="consent"
                checked={formData.consent}
                onChange={(e) => setFormData({ ...formData, consent: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-zinc-600 rounded"
                required
              />
              <label htmlFor="consent" className="ml-2 block text-sm text-zinc-300">
                I consent to DocketVista processing my data per our <Link to="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</Link>. <span className="text-red-500">*</span>
              </label>
            </div>
            {errors.consent && <p className="text-sm text-red-500">{errors.consent}</p>}
            <Button
              type="submit"
              disabled={status === "loading" || !formData.consent}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              aria-label="Submit contact form"
              aria-live="polite"
            >
              {status === "loading" ? "Sending..." : "Send Message"}
            </Button>
            {status === "error" && (
              <div className="text-center text-sm text-red-500" role="alert" aria-live="polite">
                Something went wrong. Try again or email support@docketvista.com.
              </div>
            )}
          </motion.form>

          {/* Contact Cards */}
          <motion.div {...fadeInUp} className="space-y-6">
            <Card className="bg-zinc-900/60 border border-zinc-800 rounded-2xl">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center">
                  <Mail className="h-6 w-6 mr-2 text-indigo-500" aria-hidden="true" />
                  Demo Booking
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center space-y-4">
                <p className="text-sm text-zinc-400">See AI leads in action</p>
                <a href="https://calendly.com/docketvista/demo" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline block">Book Now</a>
                <p className="text-xs text-zinc-500">15-min sessions, M-F</p>
                <Button asChild variant="outline" size="sm" className="w-full">
                  <Link to="/pricing">After Demo: Pricing</Link>
                </Button>
              </CardContent>
            </Card>
            <Card className="bg-zinc-900/60 border border-zinc-800 rounded-2xl">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center">
                  <MailOpen className="h-6 w-6 mr-2 text-indigo-500" aria-hidden="true" />
                  Support
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center space-y-4">
                <p className="text-sm text-zinc-400">Billing, leads, technical</p>
                <a href="mailto:support@docketvista.com" className="text-indigo-400 hover:underline block">support@docketvista.com</a>
                <p className="text-xs text-zinc-500">SLA: 24 Hours Email | Phone M-F 9-5 EST</p>
              </CardContent>
            </Card>
            <Card className="bg-zinc-900/60 border border-zinc-800 rounded-2xl">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center">
                  <Users className="h-6 w-6 mr-2 text-indigo-500" aria-hidden="true" />
                  Expansion
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center space-y-4">
                <p className="text-sm text-zinc-400">New states, custom features</p>
                <a href="mailto:expansion@docketvista.com" className="text-indigo-400 hover:underline block">expansion@docketvista.com</a>
                <p className="text-xs text-zinc-500">SLA: 48 Hours for Queries</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Status/Support */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.div {...fadeInUp} className="text-center space-y-4">
          <h2 className="text-2xl font-bold">Support & Status</h2>
          <div className="flex flex-wrap justify-center gap-6 text-sm">
            <Link to="/status" className="text-indigo-400 hover:underline flex items-center">
              <Clock className="h-4 w-4 mr-1" aria-hidden="true" /> System Status
            </Link>
            <Link to="/docs" className="text-indigo-400 hover:underline flex items-center">
              <FileText className="h-4 w-4 mr-1" aria-hidden="true" /> Documentation
            </Link>
            <Link to="/api-status" className="text-indigo-400 hover:underline flex items-center">
              <Zap className="h-4 w-4 mr-1" aria-hidden="true" /> API Status
            </Link>
          </div>
          <p className="text-zinc-500">Average response time: 2 hours. 99.9% uptime last month.</p>
        </motion.div>
      </section>

      {/* Map/Location */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeInUp}>
          <Card className="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <CardHeader className="bg-zinc-800 p-0">
              <div className="h-48 bg-gradient-to-r from-zinc-700 to-zinc-600 flex items-center justify-center">
                <MapPin className="h-12 w-12 text-white opacity-50" aria-hidden="true" />
                <span className="sr-only">Map Placeholder</span>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <CardTitle className="flex items-center mb-2">
                <MapPin className="h-5 w-5 mr-2 text-indigo-500" aria-hidden="true" />
                Our Location
              </CardTitle>
              <p className="text-zinc-400">DocketVista Inc.<br />123 Legal Lane, Hartford, CT 06101<br />United States</p>
            </CardContent>
          </Card>
        </motion.div>
      </section>

      {/* FAQ */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.h2 {...fadeInUp} className="text-3xl font-bold text-center mb-12">Investor Support FAQs</motion.h2>
        <Accordion type="single" collapsible className="w-full max-w-2xl mx-auto">
          <AccordionItem value="pricing">
            <AccordionTrigger>How to upgrade for more leads?</AccordionTrigger>
            <AccordionContent>Dashboard {' > '} Billing. Instant upgrade to Pro for unlimited CT multi-county. <Link to="/pricing" className="text-indigo-400">See plans</Link>.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="coverage">
            <AccordionTrigger>Current geography?</AccordionTrigger>
            <AccordionContent>CT counties now; expansion to multi-state Q1 2025. Customize in dashboard.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="trial">
            <AccordionTrigger>Trial details?</AccordionTrigger>
            <AccordionContent>7-day free on all plans—no card. Test CT leads and AI insights immediately.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="data">
            <AccordionTrigger>Lead accuracy?</AccordionTrigger>
            <AccordionContent>99% verified from public dockets. AI flags risks; 7-day guarantee if unsatisfied.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="security">
            <AccordionTrigger>Data privacy?</AccordionTrigger>
            <AccordionContent>AES-256, compliant. Your queries and leads stay private. <Link to="/security" className="text-indigo-400">Policy</Link>.</AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      {/* Bottom CTA */}
      <footer className="bg-indigo-600 py-12 text-center">
        <motion.div {...fadeInUp}>
          <h2 className="text-3xl font-bold mb-4 text-white">Ready for Your Success?</h2>
          <p className="text-indigo-100 mb-6">Demo AI leads or get support—committed to boosting your ROI.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="bg-white text-indigo-600 hover:bg-gray-100 px-8">
              <a href="https://calendly.com/docketvista/demo" target="_blank" rel="noopener noreferrer">Schedule Demo</a>
            </Button>
            <Button variant="outline" size="lg" className="border-white text-white hover:bg-white/10 px-8">
              <Link to="/pricing">View Plans</Link>
            </Button>
          </div>
        </motion.div>
      </footer>
    </div>
  );
}