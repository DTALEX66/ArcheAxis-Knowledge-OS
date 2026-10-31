import { useEffect, useState } from "react";
import Particles, { ParticlesProvider } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";
import type { ISourceOptions } from "@tsparticles/engine";
import { useAaosTheme } from "../design-system/ThemeProvider";
import "./ParticleField.css";

const options: ISourceOptions = {
  fullScreen: { enable: false },
  fpsLimit: 30,
  detectRetina: false,
  background: { color: "transparent" },
  particles: {
    number: { value: 42, density: { enable: false } },
    color: { value: ["#8ed5ff", "#4cd7f6"] },
    opacity: { value: { min: 0.04, max: 0.2 } },
    size: { value: { min: 1, max: 2.2 } },
    move: { enable: true, speed: 0.28, direction: "none", outModes: { default: "out" } },
    links: { enable: false },
  },
  interactivity: { events: { onHover: { enable: false }, onClick: { enable: false } } },
};

/** Decorative cosmic dust only; never intercepts input and is disabled for reduced motion. */
export function ParticleField() {
  const { theme } = useAaosTheme();
  const media = () => typeof window.matchMedia === "function" ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  const [reduced, setReduced] = useState(() => media()?.matches ?? false);

  useEffect(() => {
    const query = media();
    if (!query) return;
    const update = () => setReduced(query.matches);
    query.addEventListener?.("change", update);
    return () => query.removeEventListener?.("change", update);
  }, []);

  if (reduced || theme !== "cosmic") return null;
  return <ParticlesProvider init={loadSlim}>
    <Particles id="aaos-particle-field" className="aaos-particle-field" aria-hidden="true" options={options}/>
  </ParticlesProvider>;
}
