/**
 * Image Optimizer Helper
 * Handles image optimization for installation photos
 * Phase 1: Size validation and metadata preparation
 * Phase 2: Actual compression via Canvas/Sharp (future enhancement)
 */

export interface OptimizedImage {
  buffer: ArrayBuffer
  originalSize: number
  compressed: boolean
  ratio: number
}

/**
 * Optimizes an image file for storage
 * - Validates file size
 * - Prepares for compression if needed
 * - Returns buffer and metadata
 *
 * @param file - File object from FormData
 * @returns Promise with optimized buffer and metadata
 */
export async function optimizeImage(file: File): Promise<OptimizedImage> {
  if (!file) {
    throw new Error('File is required')
  }

  const originalSize = file.size
  const buffer = await file.arrayBuffer()

  // Phase 1: Size validation
  const MAX_SIZE = 2 * 1024 * 1024 // 2MB
  const OPTIMAL_SIZE = 500 * 1024 // 500KB target

  // If file is already small, don't need compression
  if (originalSize < OPTIMAL_SIZE) {
    return {
      buffer,
      originalSize,
      compressed: false,
      ratio: 1,
    }
  }

  // If file exceeds 2MB, mark for compression
  // Phase 2: Actual compression will be implemented separately
  if (originalSize > MAX_SIZE) {
    console.warn(`Image exceeds optimal size: ${originalSize} bytes`)
    // TODO: Phase 2 - implement actual compression via Canvas or Sharp
    // For now, return as-is with compressed flag
    return {
      buffer,
      originalSize,
      compressed: false, // Will be true once Phase 2 compression is done
      ratio: 1,
    }
  }

  // File is in acceptable range (500KB - 2MB)
  return {
    buffer,
    originalSize,
    compressed: false,
    ratio: 1,
  }
}

/**
 * Validates image file type and size
 * @param file - File to validate
 * @returns true if valid
 */
export function validateImageFile(file: File): boolean {
  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
  const MAX_SIZE = 5 * 1024 * 1024 // 5MB hard limit

  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error(`Invalid image type: ${file.type}`)
  }

  if (file.size > MAX_SIZE) {
    throw new Error(`Image too large: ${file.size} bytes (max ${MAX_SIZE})`)
  }

  return true
}
