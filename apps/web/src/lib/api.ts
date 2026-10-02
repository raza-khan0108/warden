const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getGitHubInstallUrl(): Promise<string> {
  const response = await fetch(`${API_URL}/integrations/github/install-url`);
  if (!response.ok) {
    throw new Error("Failed to get GitHub install URL");
  }
  const data = await response.json();
  return data.install_url;
}

export async function listIntegrations(
  orgId: number,
  token: string
): Promise<Array<{ id: number; type: string; installation_id: number }>> {
  const response = await fetch(`${API_URL}/integrations/${orgId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to list integrations");
  }
  return response.json();
}

export async function getIntegration(
  orgId: number,
  integrationType: string,
  token: string
): Promise<{ id: number; type: string; installation_id: number }> {
  const response = await fetch(`${API_URL}/integrations/${orgId}/${integrationType}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to get ${integrationType} integration`);
  }
  return response.json();
}
