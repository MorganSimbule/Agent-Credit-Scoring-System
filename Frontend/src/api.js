import apiClient from "./api/client";

export const api = {
  health: async () => {
    const { data } = await apiClient.get("/");
    return data;
  },
  summary: async () => {
    const { data } = await apiClient.get("/api/logs/summary");
    return data;
  },
  recent: async (limit = 10) => {
    const { data } = await apiClient.get(`/api/logs/recent?limit=${limit}`);
    return data;
  },
};
