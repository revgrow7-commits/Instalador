/**
 * Edge Function: Checkin/Checkout with Photo Upload
 * Handles installer check-in/check-out with GPS location and photo evidence
 *
 * Endpoint: /functions/v1/checkin-checkout
 * Method: POST
 * Content-Type: multipart/form-data
 *
 * Request Fields:
 * - assignment_id: UUID (required) - Installation job assignment
 * - installer_id: UUID (required) - Installer user ID
 * - type: 'checkin' | 'checkout' (required)
 * - latitude: number (required) - GPS latitude
 * - longitude: number (required) - GPS longitude
 * - photo: File (required) - Photo evidence
 * - notes: string (optional) - Additional notes
 * - rating: number (optional, 1-5) - Quality rating (checkout only)
 * - assignment_item_id: UUID (optional) - Specific item being worked on
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { optimizeImage, validateImageFile } from './image-optimizer.ts'

// Initialize Supabase client with service role (for server-side operations)
const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

if (!supabaseUrl || !supabaseServiceKey) {
  throw new Error('Missing Supabase configuration')
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

/**
 * Validates required fields in the request
 */
function validateRequiredFields(
  assignmentId: string | null,
  installerId: string | null,
  type: string | null,
  latitude: string | null,
  longitude: string | null,
  photoFile: File | null
): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!assignmentId) errors.push('assignment_id is required')
  if (!installerId) errors.push('installer_id is required')
  if (!type) errors.push('type is required')
  if (!latitude) errors.push('latitude is required')
  if (!longitude) errors.push('longitude is required')
  if (!photoFile) errors.push('photo file is required')

  if (type && !['checkin', 'checkout'].includes(type)) {
    errors.push('type must be "checkin" or "checkout"')
  }

  if (latitude) {
    const lat = parseFloat(latitude)
    if (isNaN(lat) || lat < -90 || lat > 90) {
      errors.push('latitude must be a valid number between -90 and 90')
    }
  }

  if (longitude) {
    const lon = parseFloat(longitude)
    if (isNaN(lon) || lon < -180 || lon > 180) {
      errors.push('longitude must be a valid number between -180 and 180')
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

/**
 * Validates optional rating field
 */
function validateRating(ratingStr: string | null): { valid: boolean; value: number | null; error?: string } {
  if (!ratingStr) {
    return { valid: true, value: null }
  }

  const rating = parseInt(ratingStr, 10)
  if (isNaN(rating) || rating < 1 || rating > 5) {
    return {
      valid: false,
      value: null,
      error: 'rating must be a number between 1 and 5',
    }
  }

  return { valid: true, value: rating }
}

/**
 * Generates a unique storage path for the photo
 */
function generatePhotoPath(assignmentId: string, type: 'checkin' | 'checkout', installerId: string): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(7)
  return `${assignmentId}/${type}/${installerId}_${timestamp}_${random}.jpg`
}

/**
 * Creates checklist record in database
 */
async function createChecklistRecord(
  assignmentId: string,
  assignmentItemId: string | null,
  installerId: string,
  type: 'checkin' | 'checkout',
  latitude: number,
  longitude: number,
  photoUrl: string,
  photoMetadata: object,
  notes: string | null,
  rating: number | null
) {
  const { data, error } = await supabase
    .from('installation_checklists')
    .insert({
      assignment_id: assignmentId,
      assignment_item_id: assignmentItemId,
      installer_id: installerId,
      type,
      latitude,
      longitude,
      photo_url: photoUrl,
      photo_metadata: photoMetadata,
      notes,
      rating,
    })
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create checklist record: ${error.message}`)
  }

  return data
}

/**
 * Creates photo index record in database
 */
async function createPhotoIndexRecord(
  assignmentId: string,
  assignmentItemId: string | null,
  installerId: string,
  checklistId: string,
  photoUrl: string,
  photoKey: string,
  latitude: number,
  longitude: number,
  type: string,
  fileSize: number,
  mimeType: string
) {
  const { error } = await supabase
    .from('installation_photos')
    .insert({
      assignment_id: assignmentId,
      assignment_item_id: assignmentItemId,
      installer_id: installerId,
      checklist_id: checklistId,
      photo_url: photoUrl,
      photo_key: photoKey,
      latitude,
      longitude,
      type,
      file_size: fileSize,
      mime_type: mimeType,
    })

  if (error) {
    throw new Error(`Failed to create photo index record: ${error.message}`)
  }
}

/**
 * Updates assignment status based on checkin/checkout
 */
async function updateAssignmentStatus(assignmentId: string, type: 'checkin' | 'checkout') {
  const newStatus = type === 'checkin' ? 'em_progresso' : 'concluido'

  const { error } = await supabase
    .from('installation_job_assignments')
    .update({ status: newStatus, updated_at: new Date().toISOString() })
    .eq('id', assignmentId)

  if (error) {
    throw new Error(`Failed to update assignment status: ${error.message}`)
  }
}

/**
 * Main handler function
 */
async function handleCheckinCheckout(req: Request) {
  // CORS headers
  const headers = {
    'Content-Type': 'application/json',
  }

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return new Response('OK', { status: 200, headers })
  }

  // Only POST allowed
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed. Use POST.' }),
      { status: 405, headers }
    )
  }

  try {
    // Parse FormData
    const formData = await req.formData()

    const assignmentId = formData.get('assignment_id') as string | null
    const installerId = formData.get('installer_id') as string | null
    const type = formData.get('type') as string | null
    const latitudeStr = formData.get('latitude') as string | null
    const longitudeStr = formData.get('longitude') as string | null
    const photoFile = formData.get('photo') as File | null
    const notes = (formData.get('notes') as string | null) || null
    const ratingStr = formData.get('rating') as string | null
    const assignmentItemId = (formData.get('assignment_item_id') as string | null) || null

    // Validate required fields
    const validation = validateRequiredFields(assignmentId, installerId, type, latitudeStr, longitudeStr, photoFile)
    if (!validation.valid) {
      return new Response(
        JSON.stringify({ error: 'Validation failed', details: validation.errors }),
        { status: 400, headers }
      )
    }

    // Parse and validate numeric fields
    const latitude = parseFloat(latitudeStr!)
    const longitude = parseFloat(longitudeStr!)
    const ratingValidation = validateRating(ratingStr)

    if (!ratingValidation.valid) {
      return new Response(
        JSON.stringify({ error: 'Validation failed', details: [ratingValidation.error] }),
        { status: 400, headers }
      )
    }

    // Validate image file
    try {
      validateImageFile(photoFile!)
    } catch (error) {
      return new Response(
        JSON.stringify({ error: 'Image validation failed', details: [(error as Error).message] }),
        { status: 400, headers }
      )
    }

    // Optimize image
    const optimized = await optimizeImage(photoFile!)

    // Generate storage path
    const photoPath = generatePhotoPath(assignmentId, type as 'checkin' | 'checkout', installerId)

    // Upload to Storage
    const { data: uploadData, error: uploadError } = await supabase.storage
      .from('installation-photos')
      .upload(photoPath, new Blob([optimized.buffer], { type: 'image/jpeg' }), {
        contentType: 'image/jpeg',
        upsert: false,
      })

    if (uploadError) {
      throw new Error(`Photo upload failed: ${uploadError.message}`)
    }

    // Get public URL
    const { data: urlData } = supabase.storage
      .from('installation-photos')
      .getPublicUrl(photoPath)

    const photoUrl = urlData.publicUrl

    // Create checklist record
    const checklist = await createChecklistRecord(
      assignmentId,
      assignmentItemId,
      installerId,
      type as 'checkin' | 'checkout',
      latitude,
      longitude,
      photoUrl,
      {
        file_size: optimized.originalSize,
        mime_type: 'image/jpeg',
        compressed: optimized.compressed,
        compression_ratio: optimized.ratio,
      },
      notes,
      ratingValidation.value
    )

    // Create photo index record
    await createPhotoIndexRecord(
      assignmentId,
      assignmentItemId,
      installerId,
      checklist.id,
      photoUrl,
      photoPath,
      latitude,
      longitude,
      type as string,
      optimized.originalSize,
      'image/jpeg'
    )

    // Update assignment status
    await updateAssignmentStatus(assignmentId, type as 'checkin' | 'checkout')

    // Return success response
    return new Response(
      JSON.stringify({
        success: true,
        checklist_id: checklist.id,
        photo_url: photoUrl,
        type,
        timestamp: new Date().toISOString(),
      }),
      { status: 201, headers }
    )
  } catch (error) {
    console.error('Error in checkin-checkout handler:', error)
    return new Response(
      JSON.stringify({
        error: 'Failed to process checkin/checkout',
        details: (error as Error).message,
      }),
      { status: 500, headers }
    )
  }
}

// Export the handler for Deno
Deno.serve(handleCheckinCheckout)
