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
  async (config) => {
    if (typeof window !== "undefined" && config.url?.includes("/wallet")) {
      const encryptedprivateKey = localStorage.getItem("privateKey")
      if (encryptedprivateKey) {
        try {
          // Synchronously decrypt private key (assumes decryptprivateKey is sync or promisified correctly)
          const privateKey = await decryptprivateKey(encryptedprivateKey, "aligthage.online.v2")
          config.headers.Authorization = `Bearer ${privateKey}`
        } catch (err) {
          console.error("Failed to decrypt private key:", err)
        }
      }
    }
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
    return response
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
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
          window.location.pathname !== "/wallet"
        ) {
          window.location.href = "/wallet/import"
        }
      } else if (status === 400) {
        toast({
          title: "Invalid Request",
          description: data.error || "Please check your input and try again.",
          variant: "destructive",
        })
      } else if (status === 404) {
        toast({
          title: "Not Found",
          description: data.error || "The requested resource was not found.",
          variant: "destructive",
        })
      } else if (status === 415) {
        toast({
          title: "Unsupported Media Type",
          description: "The server doesn't accept the data format sent.",
          variant: "destructive",
        })
        console.error("Content-Type mismatch. Check API request headers.")
      } else if (status >= 500) {
        toast({
          title: "Server Error",
          description: "Something went wrong on the server. Please try again later.",
          variant: "destructive",
        })
      }
    } else if (error.request) {
      toast({
        title: "Network Error",
        description: "Unable to connect to the server. Please check your internet connection.",
        variant: "destructive",
      })
    } else {
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
        const response = await apiClient.post("/wallet", {})
        return response.data
      } catch (error) {
        throw error
      }
    },

    import: async (privateKey: string) => {
      try {
        const response = await apiClient.post("/wallet", { private_key: privateKey })
        return response.data
      } catch (error) {
        throw error
      }
    },

    transact: async (recipient: string, amount: number, options: { priority: string }) => {
      const priorityOptions = ["low", "medium", "high"]
      if (!priorityOptions.includes(options.priority)) {
        throw new Error("Invalid priority option")
      }
      try {
        const response = await apiClient.post("/wallet/transact", {
          recipient,
          amount: Number(amount),
          priority: options.priority
        })
        return response.data
      } catch (error) {
        throw error
      }
    },

    getFeeRate: async () => {
      try {
        const response = await apiClient.get("/fee-rate")
        return response.data
      } catch (error) {
        throw error
      }
    }
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

    getRange: async (start: number, end: number, reverse: boolean = false) => {
      try {
        const response = await apiClient.get(
          `/blockchain/range?start=${start}&end=${end}&reverse=${reverse}`
        )
        return response.data
      } catch (error) {
        throw error
      }
    },

    getPaginated: async (page: number = 1, pageSize: number = 10) => {
      try {
        const response = await apiClient.get(
          `/blockchain/paginated?page=${page}&page_size=${pageSize}`
        )
        return response.data
      } catch (error) {
        throw error
      }
    },

    getLatest: async (limit: number = 10) => {
      try {
        const response = await apiClient.get(`/blockchain/latest?limit=${limit}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getHeight: async () => {
      try {
        const response = await apiClient.get("/blockchain/height")
        return response.data
      } catch (error) {
        throw error
      }
    },

    getBlock: async (blockId: string) => {
      try {
        if (!isNaN(Number(blockId))) {
          const response = await apiClient.get(`/blockchain/height/${blockId}`)
          return response.data
        }
        const response = await apiClient.get(`/blockchain/hash/${blockId}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getBlockByHeight: async (height: number) => {
      try {
        const response = await apiClient.get(`/blockchain/height/${height}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getBlockByHash: async (blockHash: string) => {
      try {
        const response = await apiClient.get(`/blockchain/hash/${blockHash}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getTransaction: async (txId: string) => {
      try {
        const response = await apiClient.get(`/blockchain/tx/${txId}`)
        return response.data
      } catch (error) {
        throw error
      }
    },

    getHalvingInfo: async () => {
      try {
        const response = await apiClient.get("/blockchain/halving")
        return response.data
      } catch (error) {
        throw error
      }
    }
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

    getbyId: async (txId: string) => {
      try {
        const response = await apiClient.get(`/transaction/id/${txId}`)
        return response.data
      } catch (error) {
        throw error
      }
    },
  },
}