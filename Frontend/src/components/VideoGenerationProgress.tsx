import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { Check } from "lucide-react";
import { VideoPlayer } from "./VideoPlayer";

interface Agent {
  id: string;
  name: string;
  description: string;
  duration: number;
  imageAnimation: string;
  generatedText: string;
}

const agents: Agent[] = [
  {
    id: "scraper",
    name: "Extracting Article",
    description: "Reading and parsing the article content",
    duration: 3000,
    imageAnimation: "scan",
    generatedText: "Extracted 1,247 words from article"
  },
  {
    id: "script",
    name: "Script Writer",
    description: "Creating a compelling narrative",
    duration: 4000,
    imageAnimation: "flip",
    generatedText: "Generated 8 scene scripts"
  },
  {
    id: "storyboard",
    name: "Storyboard",
    description: "Generating visual scenes",
    duration: 5000,
    imageAnimation: "rotate",
    generatedText: "Created 12 storyboard frames"
  },
  {
    id: "styler",
    name: "Styler",
    description: "Applying your selected visual style",
    duration: 4000,
    imageAnimation: "pulse",
    generatedText: "Applied style to all frames"
  },
  {
    id: "motion",
    name: "Motion Designer",
    description: "Adding smooth animations",
    duration: 4500,
    imageAnimation: "shake",
    generatedText: "Added 24 motion transitions"
  },
  {
    id: "assets",
    name: "Asset Manager",
    description: "Organizing media assets",
    duration: 2500,
    imageAnimation: "bounce",
    generatedText: "Organized 36 media files"
  },
  {
    id: "voice",
    name: "Voice Actor",
    description: "Generating voice narration",
    duration: 4000,
    imageAnimation: "glow",
    generatedText: "Generated 45s of narration"
  },
  {
    id: "editor",
    name: "Editor",
    description: "Compiling the final video",
    duration: 5000,
    imageAnimation: "zoom",
    generatedText: "Compiled 1080p video"
  },
];

interface VideoGenerationProgressProps {
  selectedStyle: string | null;
  onComplete?: () => void;
}

interface LogEntry {
  agentId: string;
  agentName: string;
  status: "started" | "completed";
  description: string;
  generatedText?: string;
  time: string;
  duration?: string;
}

export const VideoGenerationProgress = ({ selectedStyle, onComplete }: VideoGenerationProgressProps) => {
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0);
  const [agentProgress, setAgentProgress] = useState(0);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [startTime] = useState(Date.now());
  const [agentStartTime, setAgentStartTime] = useState(Date.now());

  const cardRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLDivElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const overallProgress = Math.min(
    ((completedAgents.length + (isComplete ? 0 : agentProgress / 100)) / agents.length) * 100,
    100
  );

  const getTimeString = () => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const mins = Math.floor(elapsed / 60);
    const secs = elapsed % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Add started log when agent changes
  useEffect(() => {
    if (currentAgentIndex < agents.length) {
      const agent = agents[currentAgentIndex];
      setAgentStartTime(Date.now());
      setLogs(prev => [...prev, {
        agentId: agent.id,
        agentName: agent.name,
        status: "started",
        description: agent.description,
        time: getTimeString(),
      }]);
    }
  }, [currentAgentIndex]);

  // Card entry animation (only once to avoid blinking between sub-steps)
  useEffect(() => {
    if (cardRef.current && currentAgentIndex === 0) {
      gsap.fromTo(cardRef.current,
        { opacity: 0, y: 15, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power2.out" }
      );
    }
  }, [currentAgentIndex]);

  // Progress animation for each agent
  useEffect(() => {
    if (currentAgentIndex >= agents.length) {
      setIsComplete(true);
      setTimeout(() => setShowVideoPlayer(true), 2000);
      return;
    }

    const agent = agents[currentAgentIndex];
    const thisAgentStartTime = Date.now();

    const progressInterval = setInterval(() => {
      const elapsed = Date.now() - thisAgentStartTime;
      const progress = Math.min((elapsed / agent.duration) * 100, 100);
      setAgentProgress(progress);

      if (progress >= 100) {
        clearInterval(progressInterval);
        setCompletedAgents(prev => [...prev, agent.id]);

        // Add completed log
        const duration = ((Date.now() - agentStartTime) / 1000).toFixed(1);
        setLogs(prev => [...prev, {
          agentId: agent.id,
          agentName: agent.name,
          status: "completed",
          description: agent.description,
          generatedText: agent.generatedText,
          time: getTimeString(),
          duration: `${duration}s`,
        }]);

        setTimeout(() => {
          setCurrentAgentIndex(prev => prev + 1);
          setAgentProgress(0);
        }, 100);
      }
    }, 50);

    return () => clearInterval(progressInterval);
  }, [currentAgentIndex, onComplete, agentStartTime]);

  const currentAgent = agents[currentAgentIndex];
  const latestLog = logs.length > 0 ? logs[logs.length - 1] : null;
  const streamLogText = latestLog
    ? latestLog.status === "completed"
      ? (latestLog.generatedText || `${latestLog.agentName} completed`)
      : `${latestLog.agentName}: ${latestLog.description}`
    : currentAgent
      ? `${currentAgent.name}: ${currentAgent.description}`
      : "Initializing stream...";

  return (
    <div className="fixed inset-0 z-50 flex bg-black overflow-hidden">
      {/* Subtle floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {Array.from({ length: 15 }).map((_, i) => (
          <div
            key={i}
            className="particle absolute w-1 h-1 rounded-full bg-white/20"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${8 + Math.random() * 4}s`,
            }}
          />
        ))}
      </div>

      {/* Main content - Center area */}
      <div className="flex-1 flex items-center justify-center relative px-4 sm:px-6">
        {/* Subtle radial glow */}
        <div className="absolute w-80 h-80 rounded-full bg-white opacity-[0.03] blur-[100px] animate-pulse-slow" />

        {showVideoPlayer ? (
          /* Inline Video Player */
          <div className="z-10 w-full max-w-md">
            <VideoPlayer inline={true} aspectRatio="9:16" onClose={onComplete} />
          </div>
        ) : (
        <div className="text-center z-10 max-w-md">
          {!isComplete ? (
            <div ref={cardRef} className="glass-portrait-shell mx-auto">
              <div className="glass-orb glass-orb-a" />
              <div className="glass-orb glass-orb-b" />
              <div className="glass-noise" />
              <div className="glass-sheen" />

              <div className="relative z-10 h-full flex flex-col items-center justify-center px-6 py-10">
                {selectedStyle && (
                  <div className="mb-8 flex justify-center">
                    <div className="relative">
                      <div
                        ref={imageRef}
                        className="w-32 h-48 rounded-2xl overflow-hidden border border-white/30 shadow-2xl"
                      >
                        <img
                          src={selectedStyle}
                          alt="Selected style"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="absolute -inset-5 bg-white/10 rounded-2xl blur-2xl -z-10" />
                    </div>
                  </div>
                )}

                <h2 className="text-[22px] font-semibold text-white mb-1.5 leading-tight tracking-tight">
                  {streamLogText}
                </h2>
                <p className="text-white/70 text-base font-medium mb-5">
                  {Math.round(overallProgress)}%
                </p>

                <div className="w-full max-w-[220px] mx-auto">
                  <div className="h-1.5 bg-white/12 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-white/90 rounded-full transition-all duration-150 relative"
                      style={{ width: `${overallProgress}%` }}
                    >
                      <div className="absolute inset-0 shimmer" />
                    </div>
                  </div>
                </div>

              </div>
            </div>
          ) : (
            // Completion
            <div className="completion-enter">
              <div className="relative mb-6">
                <div className="w-14 h-14 rounded-full border border-white/20 flex items-center justify-center mx-auto completion-ring">
                  <Check className="w-6 h-6 text-white" />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-14 h-14 rounded-full border border-white/30 success-ripple" />
                </div>
              </div>
              <h2 className="text-lg font-medium text-white mb-1.5">
                Video Ready
              </h2>
              <p className="text-white/40 text-sm">
                Your video has been generated
              </p>
            </div>
          )}
        </div>
        )}
      </div>

      {/* Right-side logs panel */}
      <aside className="relative z-20 h-full w-[340px] xl:w-[380px] border-l border-white/10 bg-[#0d0f12]/88 backdrop-blur-xl flex flex-col">
        <div className="px-4 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <span className="text-black font-semibold text-[10px]">ET</span>
            </div>
            <div>
              <h3 className="text-white text-base font-semibold leading-tight">ET News Agent</h3>
              <p className="text-white/45 text-[11px] tracking-wide uppercase">Generation log stream</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              {showVideoPlayer ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400 text-xs">Complete</span>
                </>
              ) : (
                <>
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" />
                  <span className="text-cyan-200 text-xs">Processing</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="px-4 py-3 border-b border-white/10">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-[11px] tracking-wide uppercase">Pipeline Progress</span>
              <span className="text-white/80 text-xs font-mono">{completedAgents.length}/{agents.length}</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-200 via-white to-emerald-200 rounded-full transition-all duration-500"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
          {logs.map((log, index) => (
            <div key={index} className="log-entry">
              {log.status === "started" ? (
                <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3">
                  <div className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full border border-cyan-200/30 bg-cyan-200/5 flex items-center justify-center mt-0.5 shrink-0">
                      <div className="w-1.5 h-1.5 rounded-full bg-cyan-200 pulse-dot" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-white/90 text-sm font-medium">{log.agentName}</span>
                        <span className="text-white/35 text-xs">{log.time}</span>
                      </div>
                      <p className="text-white/55 text-xs mt-1">{log.description}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-emerald-300/20 bg-emerald-300/[0.06] px-3 py-3">
                  <div className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full border border-emerald-300/35 bg-emerald-300/10 flex items-center justify-center mt-0.5 shrink-0">
                      <Check className="w-3 h-3 text-emerald-200" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-emerald-100 text-[11px] tracking-wide uppercase">Generated</span>
                        <span className="text-white/35 text-xs ml-auto">{log.duration}</span>
                      </div>
                      <p className="text-white/90 text-sm leading-relaxed">{log.generatedText}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </aside>

      {/* Animations */}
      <style>{`
        .glass-portrait-shell {
          position: relative;
          width: min(88vw, 420px);
          min-width: 300px;
          aspect-ratio: 9 / 16;
          border-radius: 30px;
          border: 1px solid rgba(255, 255, 255, 0.18);
          background: linear-gradient(155deg, rgba(255, 255, 255, 0.14) 0%, rgba(255, 255, 255, 0.04) 55%, rgba(255, 255, 255, 0.08) 100%);
          box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25);
          backdrop-filter: blur(18px) saturate(130%);
          -webkit-backdrop-filter: blur(18px) saturate(130%);
          overflow: hidden;
          animation: glassFloat 4.5s ease-in-out infinite;
        }

        .glass-orb {
          position: absolute;
          border-radius: 999px;
          filter: blur(26px);
          pointer-events: none;
          opacity: 0.6;
        }

        .glass-orb-a {
          width: 140px;
          height: 140px;
          top: -45px;
          left: -35px;
          background: rgba(122, 173, 255, 0.34);
          animation: orbShiftA 8s ease-in-out infinite;
        }

        .glass-orb-b {
          width: 150px;
          height: 150px;
          right: -52px;
          bottom: -40px;
          background: rgba(255, 255, 255, 0.26);
          animation: orbShiftB 9s ease-in-out infinite;
        }

        .glass-noise {
          position: absolute;
          inset: 0;
          opacity: 0.14;
          background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.5) 1px, transparent 0);
          background-size: 3px 3px;
          pointer-events: none;
        }

        .glass-sheen {
          position: absolute;
          inset: -45%;
          background: linear-gradient(110deg, transparent 35%, rgba(255,255,255,0.22) 50%, transparent 65%);
          transform: translateX(-58%) rotate(8deg);
          animation: glassSheen 3.8s ease-in-out infinite;
          pointer-events: none;
        }

        @keyframes glassFloat {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        @keyframes orbShiftA {
          0%, 100% { transform: translate(0, 0); opacity: 0.5; }
          50% { transform: translate(16px, 14px); opacity: 0.8; }
        }

        @keyframes orbShiftB {
          0%, 100% { transform: translate(0, 0); opacity: 0.45; }
          50% { transform: translate(-18px, -12px); opacity: 0.75; }
        }

        @keyframes glassSheen {
          0% { transform: translateX(-62%) rotate(8deg); }
          50% { transform: translateX(2%) rotate(8deg); }
          100% { transform: translateX(62%) rotate(8deg); }
        }

        /* Floating particles */
        .particle {
          animation: float linear infinite;
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); opacity: 0; }
          10% { opacity: 0.3; }
          90% { opacity: 0.3; }
          100% { transform: translateY(-100vh); opacity: 0; }
        }

        /* Rotating ring */
        .rotating-ring { animation: rotate 2s linear infinite; }
        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Pulse dot */
        .pulse-dot { animation: pulse 1.5s ease-in-out infinite; }
        @keyframes pulse {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.3); }
        }

        /* Slow pulse for glow */
        .animate-pulse-slow { animation: pulseSlow 4s ease-in-out infinite; }
        @keyframes pulseSlow {
          0%, 100% { opacity: 0.03; transform: scale(1); }
          50% { opacity: 0.06; transform: scale(1.1); }
        }

        /* Shimmer */
        .shimmer {
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
          animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        /* Image animations */
        .image-animation-scan {
          animation: scanEffect 2s ease-in-out infinite;
        }
        @keyframes scanEffect {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.02); }
        }
        .overlay-scan {
          background: linear-gradient(to bottom, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%);
          animation: scanLine 2s linear infinite;
        }
        @keyframes scanLine {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }

        .image-animation-flip {
          animation: flipEffect 3s ease-in-out infinite;
        }
        @keyframes flipEffect {
          0%, 100% { transform: perspective(400px) rotateY(0deg); }
          50% { transform: perspective(400px) rotateY(180deg); }
        }
        .overlay-flip { display: none; }

        .image-animation-rotate {
          animation: rotateEffect 4s linear infinite;
        }
        @keyframes rotateEffect {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .overlay-rotate { display: none; }

        .image-animation-pulse {
          animation: pulseEffect 1.5s ease-in-out infinite;
        }
        @keyframes pulseEffect {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255,255,255,0.2); }
          50% { transform: scale(1.05); box-shadow: 0 0 20px 5px rgba(255,255,255,0.1); }
        }
        .overlay-pulse {
          background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
          animation: pulseOverlay 1.5s ease-in-out infinite;
        }
        @keyframes pulseOverlay {
          0%, 100% { opacity: 0; }
          50% { opacity: 1; }
        }

        .image-animation-shake {
          animation: shakeEffect 0.5s ease-in-out infinite;
        }
        @keyframes shakeEffect {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-3px) rotate(-1deg); }
          75% { transform: translateX(3px) rotate(1deg); }
        }
        .overlay-shake { display: none; }

        .image-animation-bounce {
          animation: bounceEffect 1s ease-in-out infinite;
        }
        @keyframes bounceEffect {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .overlay-bounce { display: none; }

        .image-animation-glow {
          animation: glowEffect 2s ease-in-out infinite;
        }
        @keyframes glowEffect {
          0%, 100% { box-shadow: 0 0 5px rgba(255,255,255,0.2); }
          50% { box-shadow: 0 0 25px rgba(255,255,255,0.4), 0 0 50px rgba(255,255,255,0.2); }
        }
        .overlay-glow {
          background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 60%);
          animation: glowOverlay 2s ease-in-out infinite;
        }
        @keyframes glowOverlay {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }

        .image-animation-zoom {
          animation: zoomEffect 2s ease-in-out infinite;
        }
        @keyframes zoomEffect {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.15); }
        }
        .overlay-zoom {
          background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
          animation: zoomOverlay 2s linear infinite;
        }
        @keyframes zoomOverlay {
          0% { transform: translateX(-100%) translateY(-100%); }
          100% { transform: translateX(100%) translateY(100%); }
        }

        /* Step dot */
        .step-dot { transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }

        /* Completion */
        .completion-enter { animation: completionEnter 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes completionEnter {
          from { opacity: 0; transform: scale(0.9) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }

        .completion-ring { animation: ringPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
        @keyframes ringPop {
          from { transform: scale(0.8); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }

        .success-ripple { animation: ripple 1s ease-out forwards; }
        @keyframes ripple {
          from { transform: scale(1); opacity: 0.5; }
          to { transform: scale(1.8); opacity: 0; }
        }

        /* Log entries */
        .log-entry { animation: logEnter 0.3s ease-out forwards; }
        @keyframes logEnter {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};
