import React from "react";
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
import { AlertCircle, Zap, Shield, Clock, Search, Target } from "lucide-react";

/*
SEO Recommendations:
<title>About DocketVista - Unlock AI-Powered Real Estate Insights</title>
<meta name="description" content="Discover how DocketVista transforms legal filings into actionable real estate opportunities with AI. Empower your investments today." />
<meta name="keywords" content="real estate investing, AI legal data, foreclosure leads, property insights" />
*/

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "DocketVista",
  "url": "https://docketvista.com",
  "description": "AI-powered platform turning legal data into real estate investing opportunities.",
  "logo": "https://docketvista.com/logo.png",
  "contactPoint": {
    "@type": "ContactPoint",
    "contactType": "Customer Service",
    "url": "https://docketvista.com/contact",
  },
};

export default function AboutPage() {
  const fadeInUp = {
    initial: { opacity: 0, y: 30 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true },
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Nav />

      {/* JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div {...fadeInUp} className="text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">DocketVista: AI-Powered Leads for Smarter Investing</h1>
          <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">Starting in Connecticut, we're transforming legal data into investor gold with AI analysis for foreclosures, evictions, and more—driving 2x your deal flow and ROI. Join early for national expansion.</p>
          <div className="flex flex-wrap justify-center gap-4 mb-8">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-zinc-800 text-zinc-200">AI Insights</span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-zinc-800 text-zinc-200">CT-First</span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-zinc-800 text-zinc-200">National Scale</span>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="bg-[#5227FF] hover:bg-[#4F20E8] px-8">
              <Link to="/pricing">Start Free Trial</Link>
            </Button>
            <Button variant="outline" asChild size="lg" className="border-white/20 text-white hover:bg-white/10 px-8">
              <Link to="/contact">Book Demo</Link>
            </Button>
          </div>
        </motion.div>
      </section>

      {/* Value Pillars */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2 {...fadeInUp} className="text-3xl sm:text-4xl font-bold text-center mb-12">Why DocketVista Wins for Investors</motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <motion.div {...fadeInUp} className="col-span-1">
            <Card className="bg-zinc-900/50 border border-zinc-800 rounded-2xl shadow-lg">
              <CardContent className="p-6 text-center">
                <AlertCircle className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
                <h3 className="text-xl font-semibold mb-2">2x Deal Flow</h3>
                <p className="text-gray-300">AI uncovers more opportunities in CT foreclosures, liens, and evictions than basic property search tools.</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div {...fadeInUp} className="col-span-1">
            <Card className="bg-zinc-900/50 border border-zinc-800 rounded-2xl shadow-lg">
              <CardContent className="p-6 text-center">
                <Target className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
                <h3 className="text-xl font-semibold mb-2">Higher ROI</h3>
                <p className="text-gray-300">Prioritized insights with risk scores and property details for faster, profitable closes.</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div {...fadeInUp} className="col-span-1">
            <Card className="bg-zinc-900/50 border border-zinc-800 rounded-2xl shadow-lg">
              <CardContent className="p-6 text-center">
                <Shield className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
                <h3 className="text-xl font-semibold mb-2">Early Access</h3>
                <p className="text-gray-300">Be first in CT counties, with priority for national rollout—secure your edge now.</p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div {...fadeInUp} className="col-span-1">
            <Card className="bg-zinc-900/50 border border-zinc-800 rounded-2xl shadow-lg">
              <CardContent className="p-6 text-center">
                <Zap className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
                <h3 className="text-xl font-semibold mb-2">AI Edge</h3>
                <p className="text-gray-300">Beyond raw data: Customizable analysis for probates, divorces, and more across states.</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Metrics */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.h2 {...fadeInUp} className="text-3xl sm:text-4xl font-bold text-center mb-12">Investor Outcomes</motion.h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-center">
          <motion.div {...fadeInUp}>
            <div className="text-4xl font-bold text-[#5227FF] mb-2">500+</div>
            <div className="text-gray-300">CT Leads Weekly</div>
          </motion.div>
          <motion.div {...fadeInUp}>
            <div className="text-4xl font-bold text-[#5227FF] mb-2">2x</div>
            <div className="text-gray-300">Deal Close Rate</div>
          </motion.div>
          <motion.div {...fadeInUp}>
            <div className="text-4xl font-bold text-[#5227FF] mb-2">99%</div>
            <div className="text-gray-300">Accuracy Guarantee</div>
          </motion.div>
          <motion.div {...fadeInUp}>
            <div className="text-4xl font-bold text-[#5227FF] mb-2">50+</div>
            <div className="text-gray-300">States Planned</div>
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2 {...fadeInUp} className="text-3xl sm:text-4xl font-bold text-center mb-12">Our AI Edge</motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <motion.div {...fadeInUp} className="text-center">
            <Search className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
            <h3 className="text-xl font-semibold mb-2">Legal Data Scan</h3>
            <p className="text-gray-300">We monitor CT court dockets for foreclosures, liens, evictions, probates—broader than standard property databases.</p>
          </motion.div>
          <motion.div {...fadeInUp} className="text-center">
            <Zap className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
            <h3 className="text-xl font-semibold mb-2">AI Analysis</h3>
            <p className="text-gray-300">Advanced models provide urgency scores, party details, and deal potential—actionable beyond raw lists.</p>
          </motion.div>
          <motion.div {...fadeInUp} className="text-center">
            <Target className="mx-auto h-12 w-12 text-[#5227FF] mb-4" />
            <h3 className="text-xl font-semibold mb-2">Investor Insights</h3>
            <p className="text-gray-300">Customized for your strategy: Daily delivery with exclusivity, scaling to multi-state as we expand.</p>
          </motion.div>
        </div>
      </section>

      {/* Impact Statement */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.div {...fadeInUp} className="text-center">
          <p className="text-xl text-gray-300 max-w-3xl mx-auto leading-relaxed">
            Backed by legal data experts, DocketVista focuses on your ROI: From CT launch to national coverage, get early access to exclusive leads that boost your pipeline and close rates.
          </p>
        </motion.div>
      </section>

      {/* Roadmap / Vision */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2 {...fadeInUp} className="text-3xl sm:text-4xl font-bold text-center mb-12">Expansion Roadmap</motion.h2>
        <motion.ul {...fadeInUp} className="max-w-2xl mx-auto space-y-4 text-gray-300">
          <li className="flex items-start">
            <div className="bg-[#5227FF] rounded-full w-2 h-2 mt-2 mr-3 flex-shrink-0"></div>
            <span>CT Launch: County-by-county coverage now, with daily leads for investors.</span>
          </li>
          <li className="flex items-start">
            <div className="bg-[#5227FF] rounded-full w-2 h-2 mt-2 mr-3 flex-shrink-0"></div>
            <span>Q1 2025: Multi-state access—customize filters for 10+ states.</span>
          </li>
          <li className="flex items-start">
            <div className="bg-[#5227FF] rounded-full w-2 h-2 mt-2 mr-3 flex-shrink-0"></div>
            <span>Q2 2025: Full national rollout + advanced AI for predictive ROI tools.</span>
          </li>
        </motion.ul>
      </section>

      {/* FAQ */}
      <section className="py-14 sm:py-16 lg:py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 bg-zinc-900/20">
        <motion.h2 {...fadeInUp} className="text-3xl sm:text-4xl font-bold text-center mb-12">Investor FAQs</motion.h2>
        <Accordion type="single" collapsible className="w-full max-w-2xl mx-auto">
          <AccordionItem value="item-1">
            <AccordionTrigger>What makes DocketVista different from PropStream or PropertyRadar?</AccordionTrigger>
            <AccordionContent>
              We specialize in AI-analyzed legal dockets for motivated sellers (foreclosures, evictions, etc.), starting in CT with national expansion—delivering exclusive insights, not just property data.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-2">
            <AccordionTrigger>How does AI improve my ROI?</AccordionTrigger>
            <AccordionContent>
              AI prioritizes leads with deal potential, risk alerts, and customization—users see 2x close rates and faster pipelines.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-3">
            <AccordionTrigger>When will national expansion happen?</AccordionTrigger>
            <AccordionContent>
              CT now; multi-state Q1 2025, full national Q2. Early sign-ups get priority access and discounts.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-4">
            <AccordionTrigger>Is there a guarantee?</AccordionTrigger>
            <AccordionContent>
              Yes, 7-day money-back. Plus 99% accuracy on verified leads.
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      {/* CTA Band */}
      <footer className="bg-[#5227FF] py-12 text-center">
        <motion.div {...fadeInUp}>
          <h2 className="text-3xl font-bold mb-4">Ready to Boost Your Deal Flow?</h2>
          <p className="text-white/90 mb-6">Sign up for CT leads and early national access today.</p>
          <Button asChild size="lg" className="bg-white text-[#5227FF] hover:bg-gray-100 px-8">
            <Link to="/pricing">Choose Your Plan</Link>
          </Button>
        </motion.div>
      </footer>
    </div>
  );
}