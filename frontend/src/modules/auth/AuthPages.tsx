import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiPost, setToken } from "../shared/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const result = await apiPost<{ token: string }>("/api/auth/login", { email, password });
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
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const result = await apiPost<{ token: string }>("/api/auth/register", { name, email, password });
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
