#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const KREA_API_BASE = "https://api.krea.ai";

// Model mappings: user-friendly name -> API path.
// Paths verified against the official Krea API reference (docs.krea.ai),
// which uses the form `provider/model-version` (NOT made-up `/vN` slugs).
const IMAGE_MODELS = {
  // Flux (Black Forest Labs)
  "flux": "bfl/flux-1-dev",
  "flux-dev": "bfl/flux-1-dev",
  "flux-pro": "bfl/flux-1.1-pro",
  "flux-pro-ultra": "bfl/flux-1.1-pro-ultra",
  "flux-kontext": "bfl/flux-kontext",
  // Ideogram (typography)
  "ideogram": "ideogram/ideogram-3",
  "ideogram-3": "ideogram/ideogram-3",
  "ideogram-2-turbo": "ideogram/ideogram-2a-turbo",
  // Google Imagen
  "imagen-4": "google/imagen-4",
  "imagen": "google/imagen-4",
  "imagen-4-fast": "google/imagen-4-fast",
  "imagen-4-ultra": "google/imagen-4-ultra",
  "imagen-3": "google/imagen-3",
  // Krea (krea-1 is retired; alias to the current Krea 2 flagship)
  "krea-1": "krea/krea-2/large",
  "krea": "krea/krea-2/large",
  "krea-2": "krea/krea-2/large",
  "krea-2-large": "krea/krea-2/large",
  "krea-2-medium": "krea/krea-2/medium",
  "krea-2-medium-turbo": "krea/krea-2/medium-turbo",
  // OpenAI
  "chatgpt-image": "openai/gpt-image",
  "gpt-image": "openai/gpt-image",
  // Google Nano Banana
  "nano-banana": "google/nano-banana-pro",
  "nano-banana-pro": "google/nano-banana-pro",
  "nano-banana-2": "google/nano-banana-2",
  // ByteDance Seedream
  "seedream": "bytedance/seedream-4",
  "seedream-4": "bytedance/seedream-4",
  "seedream-5-lite": "bytedance/seedream-5-lite",
};

const VIDEO_MODELS = {
  // MiniMax Hailuo
  "hailuo": "minimax/hailuo",
  "hailuo-02": "minimax/hailuo-02",
  "hailuo-2.3": "minimax/hailuo-2.3",
  // Kuaishou Kling (provider segment is `kling`, version is `kling-X.Y`)
  "kling": "kling/kling-1.6",
  "kling-1.6": "kling/kling-1.6",
  "kling-2.5": "kling/kling-2.5",
  "kling-3.0": "kling/kling-3.0",
  // Runway
  "runway": "runway/gen-4.5",
  "runway-gen4": "runway/gen-4",
  "runway-gen4.5": "runway/gen-4.5",
  // Google Veo
  "veo-3": "google/veo-3",
  "veo": "google/veo-3",
  "veo-3-fast": "google/veo-3-fast",
  "veo-3.1": "google/veo-3.1",
  // Alibaba Wan
  "wan": "alibaba/wan-2.5",
  "wan-2.5": "alibaba/wan-2.5",
  // Luma Ray
  "luma": "luma/ray-2",
  "ray-2": "luma/ray-2",
};

class KreaClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  async request(endpoint, options = {}) {
    const url = `${KREA_API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Krea API error: ${response.status} - ${error.slice(0, 200)}`);
    }

    return response.json();
  }

  async generateImage(params) {
    const modelPath = IMAGE_MODELS[params.model] || IMAGE_MODELS["flux"];
    const body = {
      prompt: params.prompt,
    };
    // Each Krea model endpoint has its own request schema with
    // `additionalProperties: false`, so sizing params differ by family:
    //  - Krea 2 family: requires `aspect_ratio` + `resolution` (enum: 1K/2K/...)
    //  - All other models: require `width` + `height` (default 1024)
    if (modelPath.startsWith("krea/")) {
      body.aspect_ratio = params.aspect_ratio || "1:1";
      body.resolution = params.resolution || "1K";
    } else {
      body.width = params.width || 1024;
      body.height = params.height || 1024;
    }
    // Opt-in extras (only forwarded when supplied; some models reject them).
    if (params.negative_prompt) body.negative_prompt = params.negative_prompt;
    if (params.style_id) body.style_id = params.style_id;
    if (params.image_url) body.image_url = params.image_url;

    return this.request(`/generate/image/${modelPath}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async generateVideo(params) {
    const modelPath = VIDEO_MODELS[params.model] || VIDEO_MODELS["hailuo"];
    const body = {
      prompt: params.prompt,
    };
    // The Krea API expects `start_image` for image-to-video, and most video
    // endpoints set `additionalProperties: false` (so unknown keys like
    // `image_url`, `duration`, `aspect_ratio` cause a 422). Only forward the
    // source image, mapped to the correct field name.
    if (params.image_url) body.start_image = params.image_url;
    if (params.start_image) body.start_image = params.start_image;

    return this.request(`/generate/video/${modelPath}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async getJob(jobId) {
    return this.request(`/jobs/${jobId}`);
  }

  async listJobs(params = {}) {
    const queryParts = [];
    if (params.limit) queryParts.push(`limit=${params.limit}`);
    if (params.cursor) queryParts.push(`cursor=${encodeURIComponent(params.cursor)}`);
    if (params.status) queryParts.push(`status=${params.status}`);
    if (params.types) queryParts.push(`types=${params.types}`);
    const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
    return this.request(`/jobs${query}`);
  }

  async uploadAsset(url, name) {
    return this.request("/assets", {
      method: "POST",
      body: JSON.stringify({ url, name }),
    });
  }

  async getAsset(assetId) {
    return this.request(`/assets/${assetId}`);
  }

  async listAssets(params = {}) {
    const queryParts = [];
    if (params.limit) queryParts.push(`limit=${params.limit}`);
    if (params.cursor) queryParts.push(`cursor=${encodeURIComponent(params.cursor)}`);
    const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
    return this.request(`/assets${query}`);
  }

  async searchStyles(query, params = {}) {
    const queryParts = [`query=${encodeURIComponent(query)}`];
    if (params.limit) queryParts.push(`limit=${params.limit}`);
    return this.request(`/styles/search?${queryParts.join("&")}`);
  }

  async getStyle(styleId) {
    return this.request(`/styles/${styleId}`);
  }
}

const TOOLS = [
  {
    name: "generate_image",
    description: "Generate an image using Krea AI. Returns a job_id - use get_job to check status and get the result URL.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Text description of the image to generate",
        },
        model: {
          type: "string",
          description: "Model: flux (default), flux-pro, ideogram, imagen-4, imagen-4-ultra, krea-2 (krea-1 alias), chatgpt-image, nano-banana, nano-banana-2, seedream",
          default: "flux",
        },
        width: {
          type: "number",
          description: "Image width in pixels",
          default: 1024,
        },
        height: {
          type: "number",
          description: "Image height in pixels",
          default: 1024,
        },
        image_url: {
          type: "string",
          description: "Optional source image URL for image-to-image generation",
        },
        style_id: {
          type: "string",
          description: "Optional style ID to apply",
        },
        negative_prompt: {
          type: "string",
          description: "What to avoid in the image",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "generate_video",
    description: "Generate a video using Krea AI. Returns a job_id - use get_job to check status and get the result URL.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Text description of the video to generate",
        },
        model: {
          type: "string",
          description: "Model: hailuo (default), kling, runway, veo-3, veo-3.1, wan, luma (pika/sora are not exposed by the Krea API)",
          default: "hailuo",
        },
        image_url: {
          type: "string",
          description: "Optional source image URL for image-to-video (sent to the API as start_image)",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "get_job",
    description: "Get the status and results of a generation job. Returns status (scheduled, processing, completed, failed) and result URLs when completed.",
    inputSchema: {
      type: "object",
      properties: {
        job_id: {
          type: "string",
          description: "The job ID to check",
        },
      },
      required: ["job_id"],
    },
  },
  {
    name: "list_jobs",
    description: "List generation jobs with optional filtering",
    inputSchema: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Max jobs to return (1-1000)",
          default: 100,
        },
        status: {
          type: "string",
          description: "Filter by status: scheduled, processing, completed, failed",
        },
        types: {
          type: "string",
          description: "Filter by type (comma-separated): flux, hailuo, kling, etc.",
        },
      },
    },
  },
  {
    name: "upload_asset",
    description: "Upload an image/video to Krea for use in generations",
    inputSchema: {
      type: "object",
      properties: {
        url: {
          type: "string",
          description: "URL of the asset to upload",
        },
        name: {
          type: "string",
          description: "Optional name for the asset",
        },
      },
      required: ["url"],
    },
  },
  {
    name: "get_asset",
    description: "Get details of an uploaded asset",
    inputSchema: {
      type: "object",
      properties: {
        asset_id: {
          type: "string",
          description: "The asset ID",
        },
      },
      required: ["asset_id"],
    },
  },
  {
    name: "list_assets",
    description: "List uploaded assets",
    inputSchema: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Max assets to return (1-1000)",
          default: 100,
        },
      },
    },
  },
  {
    name: "search_styles",
    description: "Search for styles/LoRAs to use in image generation",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query",
        },
        limit: {
          type: "number",
          description: "Max results",
          default: 10,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "get_style",
    description: "Get details of a specific style",
    inputSchema: {
      type: "object",
      properties: {
        style_id: {
          type: "string",
          description: "The style ID",
        },
      },
      required: ["style_id"],
    },
  },
];

async function main() {
  const apiKey = process.env.KREA_API_KEY;

  if (!apiKey) {
    console.error("Error: KREA_API_KEY environment variable is required");
    process.exit(1);
  }

  const client = new KreaClient(apiKey);
  const server = new Server(
    {
      name: "krea-mcp",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      let result;

      switch (name) {
        case "generate_image":
          result = await client.generateImage({
            prompt: args.prompt,
            model: args.model || "flux",
            width: args.width,
            height: args.height,
            image_url: args.image_url,
            style_id: args.style_id,
            negative_prompt: args.negative_prompt,
          });
          break;

        case "generate_video":
          result = await client.generateVideo({
            prompt: args.prompt,
            model: args.model || "hailuo",
            image_url: args.image_url,
          });
          break;

        case "get_job":
          result = await client.getJob(args.job_id);
          break;

        case "list_jobs":
          result = await client.listJobs({
            limit: args.limit,
            status: args.status,
            types: args.types,
          });
          break;

        case "upload_asset":
          result = await client.uploadAsset(args.url, args.name);
          break;

        case "get_asset":
          result = await client.getAsset(args.asset_id);
          break;

        case "list_assets":
          result = await client.listAssets({ limit: args.limit });
          break;

        case "search_styles":
          result = await client.searchStyles(args.query, { limit: args.limit });
          break;

        case "get_style":
          result = await client.getStyle(args.style_id);
          break;

        default:
          throw new Error(`Unknown tool: ${name}`);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
