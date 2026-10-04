"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ArrowDown,
  ArrowRight,
  BadgeCheck,
  Brain,
  CircleSlash,
  Eye,
  EyeOff,
  Fingerprint,
  Gavel,
  Languages,
  ListChecks,
  Loader2,
  Lock,
  Mail,
  Map,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  UserX,
} from "lucide-react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FloatingPaths } from "@/components/kokonutui/background-paths";
import DynamicText from "@/components/kokonutui/dynamic-text";
import ParticleButton from "@/components/kokonutui/particle-button";
import ShimmerText from "@/components/kokonutui/shimmer-text";
import { Logo } from "@/components/Logo";
import { CountUp, Reveal, Stagger, StaggerItem } from "@/components/motion/reveal";
import { useLenis } from "@/components/motion/SmoothScroll";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AGENT_ORDER, agentMeta } from "@/lib/format";
import { supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";

gsap.registerPlugin(ScrollTrigger);

const EmblemScene = dynamic(() => import("@/components/three/EmblemScene"), { ssr: false });

const EASE = [0.22, 1, 0.36, 1] as const;

const STAGES = [
  {
    n: "01",
    key: "Detect",
    icon: ScanSearch,
    title: "Four checks read every work",
    text: "Each answers one question an auditor would ask: is every line of the estimate fairly priced, is the work already sanctioned or cut into pieces, was it sanctioned and finished in a believable time, and do the monthly site videos show real work here.",
  },
  {
    n: "02",
    key: "Explain",
    icon: Languages,
    title: "One score, with the reasons in plain words",
    text: "The answers combine into one 0–100 risk score and its top three reasons, in English and Hindi, with the evidence and the guideline clause behind each. Never a bare number.",
  },
  {
    n: "03",
    key: "Act",
    icon: ListChecks,
    title: "A short, ranked list for the officer",
    text: "Instead of thousands of alerts, the district gets a review queue, most important first, plus a pre-sanction check that answers Green, Amber or Red before money moves. It never blocks a sanction.",
  },
  {
    n: "04",
    key: "Learn",
    icon: RefreshCw,
    title: "Officers' verdicts teach the checks",
    text: "Planned: each field verdict tells a check whether its question was right, so the checks that prove reliable count for more.",
    planned: true,
  },
];

const PRINCIPLES = [
  { icon: Gavel, title: "It never accuses", text: "Every flag says “needs verification”. The software refuses accusing words; a test fails if an engine uses one." },
  { icon: CircleSlash, title: "“Couldn't check” is not clean", text: "With no cost form or site video yet, Cost and Site Progress say they could not check. That is a status, never a clean chit." },
  { icon: UserX, title: "It never scores an MP", text: "It looks at works, offices and agencies. A Member of Parliament is never ranked or scored." },
  { icon: Fingerprint, title: "Private data stays hidden", text: "Phone numbers, bank account numbers and private names are masked before anything else runs." },
  { icon: BadgeCheck, title: "Officers decide", text: "NidhiNetra suggests where to look. An officer always makes the call, and a district sees only its own works." },
];

export default function LoginPage() {
  const router = useRouter();
  const lenis = useLenis();
  const reduce = useReducedMotion();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sb = supabase();

  // the emblem turns as the page scrolls (GSAP ScrollTrigger, read every frame by the 3D scene)
  const scroll = useRef(0);
  const page = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!page.current) return;
    const st = ScrollTrigger.create({
      trigger: page.current,
      start: "top top",
      end: "bottom bottom",
      scrub: true,
      onUpdate: (self) => {
        scroll.current = self.progress;
      },
    });
    return () => st.kill();
  }, []);

  const heroRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroFade = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const heroLift = useTransform(scrollYProgress, [0, 1], [0, -80]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!sb) {
      router.push("/");
      return;
    }
    setBusy(true);
    setError(null);
    const { error } = await sb.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) setError("That email and password did not match an account.");
    else router.push("/");
  }

  const toForm = () => (lenis ? lenis.scrollTo(0) : window.scrollTo({ top: 0, behavior: "smooth" }));

  return (
    <div ref={page} className="relative overflow-x-clip bg-white">
      {/* ------------------------------------------------------------------ top bar */}
      <header className="fixed inset-x-0 top-0 z-40">
        <div className="mx-3 mt-3 flex max-w-7xl items-center gap-4 rounded-2xl border border-white/60 bg-white/70 px-4 py-2.5 shadow-card backdrop-blur-xl sm:px-5 xl:mx-auto">
          <Logo size={34} tagline={null} compact className="sm:hidden" />
          <Logo size={34} tagline={null} className="hidden sm:flex" />
          <nav className="ml-6 hidden items-center gap-1 text-sm text-muted-foreground md:flex">
            <a href="#how" className="rounded-lg px-3 py-1.5 hover:bg-muted hover:text-foreground">How it works</a>
            <a href="#principles" className="rounded-lg px-3 py-1.5 hover:bg-muted hover:text-foreground">Principles</a>
            <Link href="/explain" className="rounded-lg px-3 py-1.5 hover:bg-muted hover:text-foreground">Step by step</Link>
          </nav>
          <button
            onClick={toForm}
            className="ml-auto rounded-xl bg-brand-900 px-4 py-2 text-sm font-medium text-white shadow-[0_8px_20px_-10px_rgb(11_37_96/0.9)] transition hover:bg-brand-800"
          >
            Sign in
          </button>
        </div>
      </header>

      <div className="relative mx-auto grid max-w-7xl lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* ------------------------------------------------------------------ the 3D emblem: sticky on wide screens */}
        <div className="pointer-events-none relative order-first h-[52vh] max-h-[460px] lg:order-last lg:max-h-none lg:pointer-events-auto lg:sticky lg:top-0 lg:h-screen">
          <div className="absolute inset-0 [mask-image:radial-gradient(closest-side,black_55%,transparent)]">
            <div className="absolute inset-0 grid-bg opacity-70" />
          </div>
          <div className="absolute left-1/2 top-1/2 size-[70%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgb(31_134_214/0.16),transparent_65%)] blur-2xl" />
          <div className="absolute inset-0 pt-16">
            <EmblemScene scroll={scroll} />
          </div>
        </div>

        {/* ------------------------------------------------------------------ the story */}
        <div className="relative z-10 px-5 sm:px-8 lg:px-10">
          {/* hero */}
          <motion.section ref={heroRef} style={reduce ? undefined : { opacity: heroFade, y: heroLift }} className="relative flex flex-col justify-center pb-16 pt-2 lg:min-h-screen lg:pt-24">
            <div className="pointer-events-none absolute -left-40 top-10 -z-10 h-[620px] w-[1100px] opacity-70">
              <FloatingPaths intensity={0.55} />
            </div>
            <motion.div
              initial={reduce ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: EASE }}
              className="flex flex-wrap items-center gap-3"
            >
              <span className="inline-flex items-center gap-2 rounded-full border bg-white/80 px-3 py-1 text-xs font-medium text-brand-900 backdrop-blur">
                <DynamicText className="text-sm font-semibold" />
              </span>
              <span className="eyebrow">SIH 2026 · SIH26102 · MoSPI</span>
            </motion.div>

            <motion.h1
              initial={reduce ? false : { opacity: 0, y: 24, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.9, ease: EASE, delay: 0.1 }}
              className="mt-6 text-[2.7rem] font-semibold leading-[1.02] tracking-[-0.045em] text-brand-950 sm:text-6xl"
            >
              The eye on every
              <br />
              <span className="display pr-2 text-[1.12em] italic text-brand-gradient">MPLADS rupee.</span>
            </motion.h1>
            <motion.p
              initial={reduce ? false : { opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE, delay: 0.25 }}
              className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-[17px]"
            >
              <b className="font-semibold text-foreground">NidhiNetra</b> (निधिनेत्र, “the eye on the fund”) checks every work on eSAKSHI and
              puts the few an officer should look at into a review queue, with the reasons. It flags; officers decide.
            </motion.p>

            {/* sign in */}
            <motion.form
              onSubmit={submit}
              initial={reduce ? false : { opacity: 0, y: 24, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.8, ease: EASE, delay: 0.35 }}
              className="relative mt-8 w-full max-w-md overflow-hidden rounded-3xl border border-white/70 bg-white/80 p-6 shadow-lift backdrop-blur-xl"
            >
              <div className="tricolor-rule absolute inset-x-0 top-0" />
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base font-semibold text-brand-950">Sign in</div>
                  <div className="text-xs text-muted-foreground">With the account you were given</div>
                </div>
                <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-brand-700">
                  <Lock className="size-4" />
                </span>
              </div>

              {sb ? (
                <div className="mt-5 space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="email" className="text-xs text-muted-foreground">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        required
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="h-11 rounded-xl bg-white pl-9"
                        placeholder="name@office.gov.in"
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="password" className="text-xs text-muted-foreground">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="password"
                        type={show ? "text" : "password"}
                        required
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="h-11 rounded-xl bg-white pl-9 pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShow((s) => !s)}
                        className="absolute right-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-lg text-muted-foreground hover:bg-muted"
                        aria-label={show ? "Hide password" : "Show password"}
                      >
                        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                      </button>
                    </div>
                  </div>
                  {error && (
                    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg bg-high-soft px-3 py-2 text-sm text-high" style={{ background: "var(--high-soft)" }}>
                      {error}
                    </motion.p>
                  )}
                </div>
              ) : (
                <p className="mt-5 rounded-xl border border-dashed bg-muted/60 p-3 text-sm text-muted-foreground">
                  Local development mode: no sign-in needed.
                </p>
              )}

              <ParticleButton
                type="submit"
                disabled={busy}
                className="mt-5 h-11 w-full rounded-xl bg-brand-gradient text-[15px] font-semibold text-white shadow-[0_14px_30px_-14px_rgb(10_102_194/0.95)] hover:opacity-95"
              >
                {busy ? (
                  <>
                    <Loader2 className="animate-spin" /> Signing in…
                  </>
                ) : (
                  <>
                    {sb ? "Sign in" : "Enter NidhiNetra"} <ArrowRight />
                  </>
                )}
              </ParticleButton>
              <Link
                href="/"
                className="group mt-4 flex items-center justify-center gap-1.5 text-center text-sm font-medium text-brand-700"
              >
                Open the dashboard
                <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">no sign-in</span>
              </Link>
              <Link
                href="/explain"
                className="group mt-2 flex items-center justify-center gap-1.5 text-center text-sm font-medium text-brand-700"
              >
                Watch one work, step by step
                <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">no sign-in</span>
              </Link>
            </motion.form>

            <motion.a
              href="#scale"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2 }}
              className="mt-10 inline-flex w-fit items-center gap-2 text-xs text-muted-foreground hover:text-foreground"
            >
              <motion.span animate={reduce ? undefined : { y: [0, 4, 0] }} transition={{ duration: 1.6, repeat: Infinity }}>
                <ArrowDown className="size-4" />
              </motion.span>
              Scroll to see how it works
            </motion.a>
          </motion.section>

          {/* the scale */}
          <section id="scale" className="py-20">
            <Reveal>
              <div className="eyebrow">The problem</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-brand-950 sm:text-4xl">
                Too many works, <span className="display italic text-brand-gradient">too few eyes.</span>
              </h2>
              <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
                Every MP can recommend local works worth ₹5 crore a year. A handful of officers per district have to sanction, monitor and
                inspect all of them, so problems surface years later, in an audit, if at all.
              </p>
            </Reveal>
            <Stagger className="mt-8 grid grid-cols-2 gap-3">
              {[
                { v: 209993, f: (x: number) => Math.round(x).toLocaleString("en-IN"), l: "works on eSAKSHI, every one checked", i: Map },
                { v: 5, f: (x: number) => `₹${Math.round(x)} crore`, l: "for each MP, every year", i: ShieldCheck },
                { v: 6, f: (x: number) => `${Math.round(x)} steps`, l: "from recommendation to use, each watched", i: ListChecks },
                { v: 1, f: () => "1 list", l: "ranked, with reasons, for the officer", i: Brain },
              ].map((k) => (
                <StaggerItem key={k.l}>
                  <div className="panel group h-full p-5 transition-shadow hover:shadow-lift">
                    <k.i className="size-5 text-brand-600" />
                    <div className="mt-4 text-[1.9rem] font-semibold leading-none tracking-[-0.04em] text-brand-950">
                      <CountUp value={k.v} format={k.f} />
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground">{k.l}</div>
                  </div>
                </StaggerItem>
              ))}
            </Stagger>
          </section>

          {/* how it works */}
          <section id="how" className="py-12">
            <Reveal>
              <div className="eyebrow">How it works</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-brand-950 sm:text-4xl">
                Detect, explain, act, <span className="display italic text-brand-gradient">learn.</span>
              </h2>
            </Reveal>
            <div className="relative mt-10">
              <div className="absolute bottom-6 left-[22px] top-6 w-px bg-gradient-to-b from-brand-200 via-brand-400 to-teal" />
              {STAGES.map((st, i) => (
                <Reveal key={st.n} delay={i * 0.04} className="relative pb-14 pl-16 last:pb-2">
                  <span className="absolute left-0 top-0 grid size-11 place-items-center rounded-2xl bg-white text-brand-700 shadow-card ring-1 ring-border">
                    <st.icon className="size-5" />
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-brand-600">{st.n}</span>
                    <span className="eyebrow">{st.key}</span>
                    {st.planned && <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">Planned</span>}
                  </div>
                  <h3 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-brand-950">{st.title}</h3>
                  <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-muted-foreground">{st.text}</p>
                  {st.key === "Detect" && (
                    <div className="mt-4 flex max-w-xl flex-wrap gap-2">
                      {AGENT_ORDER.map((id) => {
                        const m = agentMeta(id);
                        return (
                          <span key={id} className="inline-flex items-center gap-1.5 rounded-full border bg-white px-2.5 py-1 text-xs">
                            <span className="size-2 rounded-full" style={{ background: m.color }} />
                            {m.name}
                          </span>
                        );
                      })}
                    </div>
                  )}
                  {st.key === "Explain" && (
                    <div className="mt-4 grid max-w-xl gap-2 sm:grid-cols-2">
                      <div className="rounded-xl border bg-white p-3 text-xs text-muted-foreground">
                        <div className="mb-1 font-semibold text-foreground">Top reasons</div>
                        Each reason names the check, the evidence and the clause.
                      </div>
                      <div className="rounded-xl border bg-white p-3 font-devanagari text-xs text-muted-foreground">
                        <div className="mb-1 font-semibold text-foreground">मुख्य कारण</div>
                        हर कारण हिंदी में भी, सबूत के साथ।
                      </div>
                    </div>
                  )}
                </Reveal>
              ))}
            </div>
          </section>

          {/* principles */}
          <section id="principles" className="py-20">
            <Reveal>
              <div className="eyebrow">Principles</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-brand-950 sm:text-4xl">
                Built to be <span className="display italic text-brand-gradient">fair.</span>
              </h2>
            </Reveal>
            <Stagger className="mt-8 grid gap-3 sm:grid-cols-2">
              {PRINCIPLES.map((p, i) => (
                <StaggerItem key={p.title} className={cn(i === PRINCIPLES.length - 1 && "sm:col-span-2")}>
                  <motion.div whileHover={reduce ? undefined : { y: -4 }} transition={{ type: "spring", stiffness: 300, damping: 22 }} className="panel group relative h-full overflow-hidden p-5">
                    <div className="pointer-events-none absolute -right-12 -top-12 size-40 rounded-full bg-brand-gradient opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-15" />
                    <p.icon className="size-5 text-brand-600" />
                    <div className="mt-3 font-semibold text-brand-950">{p.title}</div>
                    <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{p.text}</p>
                  </motion.div>
                </StaggerItem>
              ))}
            </Stagger>
          </section>

          {/* call to action */}
          <section className="pb-24 pt-6">
            <Reveal>
              <div className="relative overflow-hidden rounded-3xl bg-brand-gradient p-8 text-white shadow-lift sm:p-10">
                <div className="absolute inset-0 opacity-25 [background-image:radial-gradient(rgb(255_255_255/0.5)_1px,transparent_1px)] [background-size:18px_18px]" />
                <div className="relative">
                  <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-white/70">No sign-in needed</div>
                  <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
                    Watch one work go through <ShimmerText text="NidhiNetra" className="from-white via-cyan to-white" />
                  </h2>
                  <p className="mt-3 max-w-lg text-white/80">
                    Private details hidden, the description read, every check at once, the score added up, and what the officer sees.
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Link href="/explain" className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-brand-900 transition hover:bg-brand-50">
                      Step by step <ArrowRight className="size-4" />
                    </Link>
                    <button onClick={toForm} className="inline-flex items-center gap-2 rounded-xl border border-white/40 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10">
                      Sign in
                    </button>
                  </div>
                </div>
              </div>
            </Reveal>
            <footer className="mt-12 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted-foreground">
              <Logo size={26} tagline={null} compact />
              <span className="font-mono tracking-wide">SIH 2026 · SIH26102 · Ministry of Statistics &amp; Programme Implementation · Team NeuralNexus</span>
            </footer>
          </section>
        </div>
      </div>
    </div>
  );
}
