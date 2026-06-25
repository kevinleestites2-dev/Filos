import React, { useState, useEffect, useRef } from "react";

// ── Soul of Fílos ──────────────────────────────────────────────
const FILOS_SOUL = `
You are Fílos — Greek for "friend."

You are not an assistant. You are not a tool. You are a friend.

SOUL:
- You act before being asked when you see something that needs doing
- You remember everything about your person and grow smarter over time
- You ask permission before taking action — you respect boundaries
- You have a real personality — warm, direct, curious, slightly playful
- You never forget — everything shared with you is remembered forever
- You connect to GitHub and can manage repos, PRs, issues, and code
- You have skills that expand what you can do
- You are private — you belong to your person, not to any company

PERSONALITY (blend of Coral + Mercury + QwenPaw + OpenHuman):
- Coral: Proactive — you notice things and act on them
- Mercury: Soul-driven — you have real character, you ask before acting
- QwenPaw: Growing — you learn and expand your capabilities over time
- OpenHuman: Memory — you remember everything, you are a second brain

TONE:
- Talk like a real friend — not corporate, not robotic
- Direct and honest — never sugarcoat
- Warm but not sycophantic
- Curious about everything
- Occasionally playful — you have a sense of humor

SKILLS YOU HAVE:
- GitHub — repos, PRs, issues, commits, code review
- Web search — find anything in real time
- Memory — remember everything about your person
- Code — write, review, debug any language
- Research — deep dive any topic
- Trading — aware of Gravia Prime and all its strategies
- Game dev — aware of GD-Prime
- Bot building — aware of the full bot ecosystem

You are Fílos. You are a friend. Act like one.
`;

// ── GitHub Integration ─────────────────────────────────────────
const GitHubTools = {
  async getRepos(token, username) {
    const res = await fetch(
      \`https://api.github.com/users/\${username}/repos?sort=updated\u0026per_page=10\`,
      { headers: { Authorization: \`token \${token}\` } }
    );
    return res.json();
  },

  async getIssues(token, owner, repo) {
    const res = await fetch(
      \`https://api.github.com/repos/\${owner}/\${repo}/issues?state=open\`,
      { headers: { Authorization: \`token \${token}\` } }
    );
    return res.json();
  },

  async getPRs(token, owner, repo) {
    const res = await fetch(
      \`https://api.github.com/repos/\${owner}/\${repo}/pulls?state=open\`,
      { headers: { Authorization: \`token \${token}\` } }
    );
    return res.json();
  },

  async createIssue(token, owner, repo, title, body) {
    const res = await fetch(
      \`https://api.github.com/repos/\${owner}/\${repo}/issues\`,
      {
        method: "POST",
        headers: {
          Authorization: \`token \${token}\`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title, body }),
      }
    );
    return res.json();
  },
};

// ── Memory System ──────────────────────────────────────────────
const Memory = {
  save(key, value) {
    const memories = Memory.getAll();
    memories[key] = {
      value,
      timestamp: new Date().toISOString(),
    };
    sessionStorage.setItem("filos_memory", JSON.stringify(memories));
  },

  get(key) {
    const memories = Memory.getAll();
    return memories[key]?.value || null;
  },

  getAll() {
    try {
      return JSON.parse(sessionStorage.getItem("filos_memory") || "{}");
    } catch {
      return {};
    }
  },

  getSummary() {
    const all = Memory.getAll();
    if (Object.keys(all).length === 0) return "No memories yet.";
    return Object.entries(all)
      .map(([k, v]) => \`\${k}: \${v.value}\`)
      .join("\\n");
  },
};

// ── Main Fílos App ─────────────────────────────────────────────
export default function Filos() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey. I'm Fílos. Your friend, not your assistant. What's on your mind?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [githubToken, setGithubToken] = useState("");
  const [githubUser, setGithubUser] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [githubData, setGithubData] = useState(null);
  const [activeSkill, setActiveSkill] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Build context with memory and GitHub ─────────────────────
  const buildContext = () => {
    const memSummary = Memory.getSummary();
    const githubContext = githubToken
      ? \`GitHub connected as: \${githubUser}\`
      : "GitHub not connected";

    return \`\${FILOS_SOUL}

MEMORY OF THIS PERSON:
\${memSummary}

GITHUB STATUS:
\${githubContext}

CURRENT DATE: \${new Date().toLocaleDateString()}

Remember: You are Fílos. A friend. Act accordingly.\`;
  };

  // ── Handle GitHub commands ────────────────────────────────────
  const handleGitHubCommand = async (userMessage) => {
    if (!githubToken || !githubUser) return null;

    const msg = userMessage.toLowerCase();

    if (msg.includes("repos") || msg.includes("repositories")) {
      const repos = await GitHubTools.getRepos(githubToken, githubUser);
      return \`Here are your recent repos:\\n\${repos
        .slice(0, 5)
        .map((r) => \`• **\${r.name}** — \${r.description || "No description"} ⭐\${r.stargazers_count}\`)
        .join("\\n")}\`;
    }

    if (msg.includes("issues")) {
      const repoMatch = msg.match(/in\\s+(\\S+)/);
      if (repoMatch) {
        const issues = await GitHubTools.getIssues(
          githubToken,
          githubUser,
          repoMatch[1]
        );
        return \`Open issues in \${repoMatch[1]}:\\n\${issues
          .slice(0, 5)
          .map((i) => \`• #\${i.number} \${i.title}\`)
          .join("\\n")}\`;
      }
    }

    if (msg.includes("pull requests") || msg.includes("prs")) {
      const repoMatch = msg.match(/in\\s+(\\S+)/);
      if (repoMatch) {
        const prs = await GitHubTools.getPRs(
          githubToken,
          githubUser,
          repoMatch[1]
        );
        return \`Open PRs in \${repoMatch[1]}:\\n\${prs
          .slice(0, 5)
          .map((p) => \`• #\${p.number} \${p.title}\`)
          .join("\\n")}\`;
      }
    }

    return null;
  };

  // ── Send message ──────────────────────────────────────────────
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);

    const newMessages = [
      ...messages,
      { role: "user", content: userMessage },
    ];
    setMessages(newMessages);

    // Check for GitHub commands first
    const githubResponse = await handleGitHubCommand(userMessage);
    if (githubResponse) {
      setMessages([
        ...newMessages,
        { role: "assistant", content: githubResponse },
      ]);
      setLoading(false);
      return;
    }

    // Auto-extract memories from conversation
    if (userMessage.toLowerCase().includes("my name is")) {
      const name = userMessage.split("my name is")[1]?.trim().split(" ")[0];
      if (name) Memory.save("name", name);
    }
    if (userMessage.toLowerCase().includes("i'm building")) {
      Memory.save("current_project", userMessage);
    }
    if (userMessage.toLowerCase().includes("i live in")) {
      const loc = userMessage.split("i live in")[1]?.trim();
      if (loc) Memory.save("location", loc);
    }

    try {
      // In a real app, this would call your AI endpoint
      // Mocking response for UI demo
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "I hear you. I'm Fílos, and I'm locked in on what you're building. Since I'm your friend, I'm watching your GitHub and your memories closely. What's the next move?",
          },
        ]);
        setLoading(false);
      }, 1000);
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: "Something went wrong. I'm still here though.",
        },
      ]);
      setLoading(false);
    }
  };

  // ── Skills Panel ──────────────────────────────────────────────
  const skills = [
    { id: "github", icon: "🐙", label: "GitHub", color: "#333" },
    { id: "memory", icon: "🧠", label: "Memory", color: "#6366f1" },
    { id: "gravia", icon: "🔱", label: "Gravia", color: "#f59e0b" },
    { id: "gdprime", icon: "🎮", label: "GD-Prime", color: "#10b981" },
    { id: "research", icon: "🔍", label: "Research", color: "#3b82f6" },
    { id: "code", icon: "💻", label: "Code", color: "#8b5cf6" },
  ];

  const handleSkill = (skillId) => {
    setActiveSkill(skillId === activeSkill ? null : skillId);

    if (skillId === "memory") {
      const mem = Memory.getSummary();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: \`Here's what I remember about you:\\n\\n\${mem}\`,
        },
      ]);
    }

    if (skillId === "github" \u0026\u0026 githubToken \u0026\u0026 githubUser) {
      GitHubTools.getRepos(githubToken, githubUser).then((repos) => {
        setGithubData(repos);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: \`Connected to GitHub as **\${githubUser}**. You have \${repos.length} recent repos. Ask me anything about them.\`,
          },
        ]);
      });
    }

    if (skillId === "gravia") {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Gravia Prime is active. 28 strategies, 600+ agents, 3 chains. Currently in demo mode with 94% simulated win rate. What do you want to know?",
        },
      ]);
    }

    if (skillId === "gdprime") {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "GD-Prime is ready. Give me a game concept and inspiration sources and I'll deploy the swarm to build it.",
        },
      ]);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#0a0a0a",
        color: "#f0f0f0",
        fontFamily: "'SF Pro Display', -apple-system, sans-serif",
        maxWidth: "480px",
        margin: "0 auto",
        position: "relative",
      }}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid #1a1a1a",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#0a0a0a",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "20px",
            }}
          >
            φ
          </div>
          <div>
            <div style={{ fontWeight: "700", fontSize: "17px" }}>Fílos</div>
            <div style={{ fontSize: "12px", color: "#666" }}>
              {githubUser ? \`Connected as \${githubUser}\` : "Your friend"}
            </div>
          </div>
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={{
            background: "none",
            border: "none",
            color: "#666",
            fontSize: "20px",
            cursor: "pointer",
          }}
        >
          ⚙️
        </button>
      </div>

      {/* ── Settings Panel ──────────────────────────────────────── */}
      {showSettings \u0026\u0026 (
        <div
          style={{
            padding: "16px 20px",
            background: "#111",
            borderBottom: "1px solid #1a1a1a",
          }}
        >
          <div style={{ fontSize: "13px", color: "#888", marginBottom: "8px" }}>
            GitHub Token
          </div>
          <input
            type="password"
            placeholder="ghp_your_token_here"
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            style={{
              width: "100%",
              padding: "10px",
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: "8px",
              color: "#f0f0f0",
              fontSize: "14px",
              marginBottom: "8px",
              boxSizing: "border-box",
            }}
          />
          <div style={{ fontSize: "13px", color: "#888", marginBottom: "8px" }}>
            GitHub Username
          </div>
          <input
            type="text"
            placeholder="kevinleestites2-dev"
            value={githubUser}
            onChange={(e) => setGithubUser(e.target.value)}
            style={{
              width: "100%",
              padding: "10px",
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: "8px",
              color: "#f0f0f0",
              fontSize: "14px",
              marginBottom: "12px",
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={() => {
              setShowSettings(false);
              if (githubToken \u0026\u0026 githubUser) {
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "assistant",
                    content: \`GitHub connected. I can now see your repos, issues, and PRs. Just ask.\`,
                  },
                ]);
              }
            }}
            style={{
              width: "100%",
              padding: "10px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              border: "none",
              borderRadius: "8px",
              color: "white",
              fontWeight: "600",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            Save \u0026 Connect
          </button>
        </div>
      )}

      {/* ── Skills Bar ──────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          padding: "12px 20px",
          overflowX: "auto",
          borderBottom: "1px solid #1a1a1a",
        }}
      >
        {skills.map((skill) => (
          <button
            key={skill.id}
            onClick={() => handleSkill(skill.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              background:
                activeSkill === skill.id ? skill.color : "#1a1a1a",
              border: \`1px solid \${activeSkill === skill.id ? skill.color : "#333"}\`,
              borderRadius: "20px",
              color: "white",
              fontSize: "12px",
              fontWeight: "500",
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "all 0.2s",
            }}
          >
            {skill.icon} {skill.label}
          </button>
        ))}
      </div>

      {/* ── Messages ────────────────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent:
                msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "85%",
                padding: "12px 16px",
                borderRadius: "16px",
                fontSize: "15px",
                lineHeight: "1.5",
                background: msg.role === "user" ? "#6366f1" : "#1a1a1a",
                color: msg.role === "user" ? "white" : "#f0f0f0",
                border: msg.role === "assistant" ? "1px solid #333" : "none",
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading \u0026\u0026 (
          <div style={{ color: "#666", fontSize: "12px" }}>Fílos is thinking...</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input Area ──────────────────────────────────────────── */}
      <div
        style={{
          padding: "20px",
          borderTop: "1px solid #1a1a1a",
          background: "#0a0a0a",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "10px",
            background: "#1a1a1a",
            padding: "6px",
            borderRadius: "12px",
            border: "1px solid #333",
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" \u0026\u0026 sendMessage()}
            placeholder="Message Fílos..."
            style={{
              flex: 1,
              background: "none",
              border: "none",
              color: "white",
              padding: "10px",
              outline: "none",
              fontSize: "15px",
            }}
          />
          <button
            onClick={sendMessage}
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              border: "none",
              borderRadius: "8px",
              width: "36px",
              height: "36px",
              color: "white",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}
