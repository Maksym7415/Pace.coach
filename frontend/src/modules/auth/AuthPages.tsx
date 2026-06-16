import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiPost, setToken } from "../shared/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const result = await apiPost<{ token: string }>("/api/auth/login", { identifier, password });
    if (!result.success || !result.token) {
      setError(result.error ?? "Login failed");
      return;
    }
    setToken(result.token);
    navigate("/athlete");
  }

  return (
    <div className="card stack">
      <h1>Sign in</h1>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          Email or Username
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            type="text"
            required
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Sign in</button>
      </form>
      <p className="muted">
        No account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const result = await apiPost<{ token: string }>("/api/auth/register", {
      username,
      name,
      email,
      password,
    });
    if (!result.success || !result.token) {
      setError(result.error ?? "Registration failed");
      return;
    }
    setToken(result.token);
    navigate("/athlete");
  }

  return (
    <div className="card stack">
      <h1>Create account</h1>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            pattern="^[a-zA-Z0-9_]{3,30}$"
            title="3–30 characters: letters, numbers, underscore only"
            required
          />
        </label>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Register</button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}
