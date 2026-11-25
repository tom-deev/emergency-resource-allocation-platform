import { useEffect, useState } from "react";
import { api, API_BASE_URL, saveSession } from "../api/client";

export default function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpChallenge, setOtpChallenge] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    if (!otpChallenge || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpChallenge, secondsLeft]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);

    try {
      if (mode === "register") {
        await api.register({
          username: username.trim(),
          password,
          role: "DISPATCHER",
        });
        setInfo("Dispatcher account registered successfully. Please sign in.");
        setMode("login");
        setPassword("");
      } else {
        const result = await api.login({
          username: username.trim(),
          password,
        });

        if (result.otpRequired && result.challengeToken) {
          setOtpChallenge({
            challengeToken: result.challengeToken,
            username: result.user?.username || username.trim(),
          });
          setSecondsLeft(Number(result.expiresInSeconds || 300));
          setOtpCode("");
          setInfo(
            "A 6-digit login code has been sent to your registered email address."
          );
        } else if (result.token && result.user) {
          saveSession(result.token, result.user);
          onAuthenticated(result.user);
        } else {
          setError("Unexpected login response from server.");
        }
      }
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(event) {
    event.preventDefault();
    if (!otpChallenge) return;
    setError("");
    setInfo("");
    setLoading(true);

    try {
      const result = await api.verifyOtp({
        challengeToken: otpChallenge.challengeToken,
        otp: otpCode.trim(),
      });
      saveSession(result.token, result.user);
      onAuthenticated(result.user);
    } catch (err) {
      setError(err.message || "OTP verification failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestNewOtp() {
    setError("");
    setInfo("");
    setLoading(true);
    try {
      const result = await api.login({
        username: username.trim(),
        password,
      });
      if (result.otpRequired && result.challengeToken) {
        setOtpChallenge({
          challengeToken: result.challengeToken,
          username: result.user?.username || username.trim(),
        });
        setSecondsLeft(Number(result.expiresInSeconds || 300));
        setOtpCode("");
        setInfo(
          "A new 6-digit login code has been sent to your registered email address (previous code invalidated)."
        );
      }
    } catch (err) {
      setError(err.message || "Failed to request a new OTP.");
    } finally {
      setLoading(false);
    }
  }

  const mins = Math.floor(secondsLeft / 60);
  const secs = String(secondsLeft % 60).padStart(2, "0");

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 700 }}>
            Emergency Response Platform
          </h1>
          <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
            Cloud-Native Emergency Dispatch &amp; Resource Coordination Prototype
          </p>
        </div>

        {!otpChallenge ? (
          <>
            <div className="auth-tabs">
              <button
                type="button"
                className={`auth-tab ${mode === "login" ? "active" : ""}`}
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab ${mode === "register" ? "active" : ""}`}
                onClick={() => {
                  setMode("register");
                  setError("");
                  setInfo("");
                }}
              >
                Register (Dispatcher)
              </button>
            </div>

            {error && <div className="alert alert-error">{error}</div>}
            {info && <div className="alert alert-success">{info}</div>}

            <form
              onSubmit={handleSubmit}
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <div className="field">
                <label htmlFor="auth-username">Username</label>
                <input
                  id="auth-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. dispatcher1 or operator1"
                  required
                  autoComplete="username"
                />
              </div>

              <div className="field">
                <label htmlFor="auth-password">Password</label>
                <input
                  id="auth-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  required
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                />
              </div>

              {mode === "register" && (
                <div className="alert alert-info" style={{ fontSize: "12px" }}>
                  Public registration creates a <strong>DISPATCHER</strong>{" "}
                  account. <strong>RESOURCE_OPERATOR</strong> accounts are
                  provisioned internally and require two-step OTP sign-in.
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading
                  ? "Please wait..."
                  : mode === "login"
                    ? "Sign In"
                    : "Create Dispatcher Account"}
              </button>
            </form>
          </>
        ) : (
          <>
            <div className="alert alert-info" style={{ fontSize: "12px" }}>
              <div>
                <strong>Resource Operator OTP Verification</strong> for{" "}
                <code>{otpChallenge.username}</code>
                <div style={{ marginTop: "4px" }}>
                  {secondsLeft > 0 ? (
                    <>
                      Code expires in{" "}
                      <strong>
                        {mins}:{secs}
                      </strong>{" "}
                      (single-use, max 5 attempts).
                    </>
                  ) : (
                    <strong>OTP expired. Please request a new code.</strong>
                  )}
                </div>
              </div>
            </div>

            {error && <div className="alert alert-error">{error}</div>}
            {info && <div className="alert alert-success">{info}</div>}

            <form
              onSubmit={handleVerifyOtp}
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <div className="field">
                <label htmlFor="otp-input">6-Digit OTP Code</label>
                <input
                  id="otp-input"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) =>
                    setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  placeholder="Enter 6-digit OTP"
                  required
                  autoFocus
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || otpCode.length !== 6 || secondsLeft <= 0}
              >
                {loading ? "Verifying..." : "Verify OTP & Sign In"}
              </button>

              <div className="btn-row" style={{ justifyContent: "space-between" }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={loading}
                  onClick={handleRequestNewOtp}
                >
                  Request New OTP
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={loading}
                  onClick={() => {
                    setOtpChallenge(null);
                    setOtpCode("");
                    setError("");
                    setInfo("");
                  }}
                >
                  Back to Sign In
                </button>
              </div>
            </form>
          </>
        )}

        <div className="demo-box">
          <strong>API Target:</strong> <code>{API_BASE_URL}</code>
          <div style={{ marginTop: "6px" }}>
            <strong>Local Simulated Demo Accounts</strong> (when running{" "}
            <code>backend/local_server.py</code>):
            <br />
            Dispatcher (1-step): <code>dispatcher1</code> /{" "}
            <code>dispatcher123</code>
            <br />
            Resource Operator (2-step email OTP): <code>operator1</code> /{" "}
            <code>operator123</code>
          </div>
        </div>
      </div>
    </div>
  );
}
