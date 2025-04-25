import axios from "axios"
import { toast } from "@/components/ui/use-toast"
import { decryptprivateKey } from "./utils"

// Base URL for the API - use environment variable in production
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:5000"

// Create axios instance with proper configuration
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 10000, // 10 seconds timeout
})



// Add request interceptor to inject private key from localStorage
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const encryptedprivateKey = localStorage.getItem("privateKey")
      if (encryptedprivateKey && config.url?.includes("/wallet")) {
        // Decrypt private key for the request
        decryptprivateKey(encryptedprivateKey, "aligthage.online.v2").then((privateKey) => {
          config.headers.Authorization = `Bearer ${privateKey}`
        }).catch((err) => {
          console.error("Failed to decrypt private key:", err);
        });
      }
    }

    // Log outgoing requests in development


    return config
  },
  (error) => {
    console.error("Request error:", error)
    return Promise.reject(error)
  },
)

// Add response interceptor to handle common errors
apiClient.interceptors.response.use(
  (response) => {
    // Log successful responses in development

    return response
  },
  (error) => {
    // Log error responses in development


    // Handle specific error codes
    if (error.response) {
      const { status, data } = error.response

      // Handle 401 errors (unauthorized)
      if (status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("privateKey")
        }

        toast({
          title: "Authentication Error",
          description: "Your session has expired. Please log in again.",
          variant: "destructive",
        })

        if (
          typeof window !== "undefined" &&
          window.location.pathname !== "/" &&
          window.location.pathname !== "/wallet/import" &&
          window.location.pathname !== "/api/wallet"
        ) {
          window.location.href = "/wallet/import"
        }
      }
      // Handle 400 errors (bad request)
      else if (status === 400) {
        toast({
          title: "Invalid Request",
          description: data.error || "Please check your input and try again.",
          variant: "destructive",
        })
      }
      // Handle 404 errors (not found)
      else if (status === 404) {
        toast({
          title: "Not Found",
          description: data.error || "The requested resource was not found.",
          variant: "destructive",
        })
      }
      // Handle 415 errors (unsupported media type)
      else if (status === 415) {
        toast({
          title: "Unsupported Media Type",
          description: "The server doesn't accept the data format sent.",
          variant: "destructive",
        })
        console.error("Content-Type mismatch. Check API request headers.")
      }
      // Handle 500 errors (server error)
      else if (status >= 500) {
        toast({
          title: "Server Error",
          description: "Something went wrong on the server. Please try again later.",
          variant: "destructive",
        })
      }
    } else if (error.request) {
      // Network error (no response received)
      toast({
        title: "Network Error",
        description: "Unable to connect to the server. Please check your internet connection.",
        variant: "destructive",
      })
    } else {
      // Something else happened while setting up the request
      toast({
        title: "Request Error",
        description: error.message || "An unexpected error occurred.",
        variant: "destructive",
      })
    }

    return Promise.reject(error)
  },
)

// API service functions with proper error handling and type safety
export const api = {
  wallet: {
    getInfo: async () => {
      try {
        const response = await apiClient.get("/wallet/info")
        return response.data
      } catch (error) {
        throw error
      }
    },

    create: async () => {
      try {
        const response = await apiClient.post("/api/wallet")
        return response.data
      } catch (error) {
        throw error
      }
    },

    import: async (privateKey: string) => {
      try {
        const response = await apiClient.post("/api/wallet", { private_key: privateKey })
        return response.data
      } catch (error) {
        throw error
      }
    },

    transact: async (recipient: string, amount: number, fee: { fee: number }) => {
      try {
        const response = await apiClient.post("/wallet/transact", {
          recipient,
          amount: Number(amount), // Ensure amount is a number
          fee: Number(fee.fee) || 0, // Ensure fee is a number
        })
        return response.data
      } catch (error) {
        throw error
      }
    },
  },

  blockchain: {
    getAll: async () => {
      try {
        const response = await apiClient.get("/blockchain")
        return response.data
      } catch (error) {
        throw error
      }
    },

    getRange: async (start: number, end: number) => {
      try {
        const response = await apiClient.get(`/blockchain/range?start=${start}&end=${end}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getLength: async () => {
      try {
        const response = await apiClient.get("/blockchain/length")
        return response.data
      } catch (error) {
        throw error
      }
    },
  },

  transactions: {
    getPending: async () => {
      try {
        const response = await apiClient.get("/transaction")
        return response.data
      } catch (error) {
        throw error
      }
    },

    getByAddress: async (address: string) => {
      try {
        const response = await apiClient.get(`/transactions/${address}`)
        return response.data
      } catch (error) {
        throw error
      }
    },
  },
}