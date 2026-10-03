import axios from "axios";
export const api = axios.create({ baseURL: "/api", withCredentials: true });
export const errorText = (e) =>
  typeof e.response?.data?.detail === "string"
    ? e.response.data.detail
    : e.response?.status === 422
      ? "Check the required fields and values."
      : e.message || "Request failed";
export const human = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .toLowerCase();
export const clock = (value) => {
  const s = Math.floor(value || 0);
  return `${Math.floor(s / 60)
    .toString()
    .padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
};
