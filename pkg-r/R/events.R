library(R6)

# A reusable class for managing callbacks, based on Shiny's Callbacks class
Callbacks <- R6::R6Class(
  'Callbacks',
  portable = FALSE,
  public = list(
    .nextId = integer(0),
    .callbacks = NULL,

    initialize = function() {
      # NOTE: we avoid using '.Machine$integer.max' directly
      # as R 3.3.0's 'radixsort' could segfault when sorting
      # an integer vector containing this value
      self$.nextId <- as.integer(.Machine$integer.max - 1L)
      self$.callbacks <- new.env(parent = emptyenv())
    },
    
    register = function(callback) {
      if (!is.function(callback)) {
        stop("callback must be a function")
      }
      id <- as.character(self$.nextId)
      self$.nextId <- self$.nextId - 1L
      self$.callbacks[[id]] <- callback
      
      # Return unsubscribe function
      return(function() {
        if (exists(id, envir = self$.callbacks)) {
          rm(list = id, envir = self$.callbacks)
        }
      })
    },
    
    invoke = function(...) {
      # Get all callbacks
      ids <- ls(self$.callbacks)
      
      # Sort them by ID (highest/newest first)
      ids <- as.character(sort(as.integer(ids), decreasing = TRUE))
      
      # Call each callback with the provided arguments
      for (id in ids) {
        if (exists(id, envir = self$.callbacks)) {
          callback <- self$.callbacks[[id]]
          callback(...)
        }
      }
    },
    
    count = function() {
      length(ls(self$.callbacks))
    }
  )
)

# Event emitter for handling realtime events
EventEmitter <- R6::R6Class(
  "EventEmitter",
  public = list(
    handlers = NULL,
    
    initialize = function() {
      self$handlers <- new.env(parent = emptyenv())
    },
    
    # Register a handler for an event type
    on = function(event_type, callback) {
      if (!is.function(callback)) {
        stop("callback must be a function")
      }
      
      # Create callbacks container for this event type if it doesn't exist
      if (!exists(event_type, envir = self$handlers)) {
        self$handlers[[event_type]] <- Callbacks$new()
      }
      
      # Register the callback and return the unsubscribe function
      unsubscribe <- self$handlers[[event_type]]$register(callback)
      return(unsubscribe)
    },
    
    # Emit an event
    emit = function(event_type, event) {
      # Exact match handlers
      if (exists(event_type, envir = self$handlers)) {
        self$handlers[[event_type]]$invoke(event)
      }
      
      # Check for wildcard handlers (e.g., "conversation.*")
      event_parts <- strsplit(event_type, "\\.")[[1]]
      
      for (i in 1:length(event_parts)) {
        prefix <- paste(event_parts[1:i], collapse = ".")
        wildcard <- paste0(prefix, ".*")
        
        if (exists(wildcard, envir = self$handlers)) {
          self$handlers[[wildcard]]$invoke(event)
        }
      }
      
      # Global wildcard handler
      if (exists("*", envir = self$handlers)) {
        self$handlers[["*"]]$invoke(event)
      }
    }
  )
)

# Function to integrate the EventEmitter with realtime_server
# This should be called from realtime.R
attach_event_emitter <- function(realtime_controls, evt) {
  # Create event emitter
  events <- EventEmitter$new()
  
  # Add observe to handle events
  observe({
    event <- evt()
    events$emit(event$type, event)
  })
  
  # Add on() method to realtime_controls
  realtime_controls$on <- function(event_type, callback) {
    events$on(event_type, callback)
  }
  
  # Return the enhanced realtime_controls
  realtime_controls
}