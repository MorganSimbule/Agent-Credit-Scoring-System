import apiClient from "./client";

export async function predictDefault(customer) {
  const { data } = await apiClient.post("/predict", customer);
  return data;
}

export async function predictRiskCategory(customer) {
  const { data } = await apiClient.post("/predict-risk-category", customer);
  return data;
}