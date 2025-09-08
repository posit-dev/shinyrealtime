#' @import shiny
#' @import htmltools
#' @importFrom jsonlite toJSON fromJSON
#' @importFrom httr POST add_headers content
#' @importFrom fontawesome fa_i
#' @importFrom R6 R6Class
NULL

#' Create an HTMLDependency for the JS/CSS assets
#'
#' @return An HTML dependency object that provides the necessary JavaScript and CSS files
#' @export
realtimeDependency <- function() {
  htmlDependency(
    name = "shinyrealtime",
    version = "0.1.0",
    src = list(file = system.file("www", package = "shinyrealtime")),
    script = "app.js",
    stylesheet = "app.css"
  )
}

#' UI Module for real-time interactions
#'
#' Creates the UI components needed for real-time voice and text interactions
#'
#' @param id The module ID
#' @param ... Additional UI elements to include
#' @param top Top position for the microphone button
#' @param right Right position for the microphone button
#' @param bottom Bottom position for the microphone button
#' @param left Left position for the microphone button
#'
#' @return A UI definition that can be used in a Shiny app
#' @export
realtime_ui <- function(
  id,
  ...,
  top = NULL,
  right = "1.5rem",
  bottom = "1.5rem",
  left = NULL
) {
  ns <- NS(id)

  tagList(
    div(
      ...,
      realtimeDependency(),
      fixedPanel(
        tags$button(
          id = ns("mic_button"),
          span(fa_i("microphone"), class = "mic-on"),
          span(fa_i("microphone-slash"), class = "mic-off"),
          class = "btn btn-secondary mic-toggle-btn",
          title = "Click to toggle mic, hold for push-to-talk, or use spacebar"
        ),
        top = top,
        right = right,
        bottom = bottom,
        left = left,
        width = "auto",
        class = "text-center"
      ),
      class = "shinyrealtime",
      id = ns("key")
    )
  )
}

#' Server Module for real-time interactions
#'
#' Creates the server-side logic for handling real-time voice and text interactions
#'
#' @param id The module ID
#' @param model The OpenAI model to use for real-time interactions
#' @param voice The voice to use for audio output
#' @param speed The speaking speed for audio output
#' @param instructions System instructions for the AI model
#' @param tools List of tools/functions that the AI can call
#' @param api_key OpenAI API key (optional, defaults to OPENAI_API_KEY environment variable)
#' @param ... Additional parameters to pass to the OpenAI API
#'
#' @return A list of reactive objects for controlling the real-time interaction
#' @export
realtime_server <- function(
  id,
  # model = "gpt-4o-realtime-preview-2025-06-03",
  model = "gpt-realtime",
  voice = "marin",
  speed = 1.0,
  instructions = "",
  tools = list(),
  api_key = NULL,
  ...
) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Get API key from environment if not provided
    if (is.null(api_key)) {
      api_key <- Sys.getenv("OPENAI_API_KEY")
    }

    # Create a map of tools by name
    tools_by_name <- list()
    for (tool in tools) {
      tools_by_name[[tool@name]] <- S7::S7_data(tool)
    }

    # Function to send text
    send_text <- function(text, force_response = TRUE) {
      events <- list(list(
        type = "conversation.item.create",
        item = list(
          type = "message",
          role = "user",
          content = list(
            list(
              type = "input_text",
              text = text
            )
          )
        )
      ))

      if (force_response) {
        events <- c(
          events,
          list(list(
            type = "response.create"
          ))
        )
      }

      send(events)
    }

    # Generate client secret from OpenAI
    output$key <- renderText({
      if (api_key == "") {
        stop("OPENAI_API_KEY environment variable is not set.")
      }

      provider <- ellmer::chat_openai()$get_provider()
      # Prepare tools for API request
      tool_schemas <- lapply(
        tools,
        function(tool) {
          list(
            type = "function",
            name = tool@name,
            description = tool@description,
            parameters = ellmer:::as_json(provider, tool@arguments)
          )
        }
      )

      # Create the session
      res <- POST(
        url = "https://api.openai.com/v1/realtime/client_secrets",
        add_headers(
          Authorization = paste("Bearer", api_key),
          "Content-Type" = "application/json"
        ),
        body = toJSON(
          c(
            list(
              session = list(
                type = "realtime",
                model = model,
                instructions = instructions,
                audio = list(
                  input = list(
                    # TODO: Consider turning off detection when push-to-talk is used
                    turn_detection = list(type = "semantic_vad")
                  ),
                  output = list(
                    voice = voice,
                    speed = speed
                  )
                ),
                tools = tool_schemas
              )
            ),
            list(...)
          ),
          auto_unbox = TRUE
        ),
        encode = "json"
      )

      data <- content(res)
      return(jsonlite::toJSON(
        list(key = data$value, model = model),
        auto_unbox = TRUE
      ))
    })

    # Handle key events
    observeEvent(input$key_event, {
      tryCatch(
        {
          event <- evt()

          cat("-------------\n")
          cat(format(Sys.time(), "%Y-%m-%d %H:%M:%OS3"), "\n")
          cat(event$type, "\n")
          cat(input$key_event, "\n")

          if (event$type == "response.function_call_arguments.done") {
            fname <- event$name
            if (!fname %in% names(tools_by_name)) {
              stop(paste("Unknown function:", fname))
            }
            tool_fun <- tools_by_name[[fname]]

            args <- try(fromJSON(event$arguments))
            if (inherits(args, "try-error")) {
              shiny::showNotification(
                "Error: The LLM provided malformed function arguments",
                type = "error"
              )
              return(NULL)
            }

            # Execute the tool function with the arguments
            result <- do.call(tool_fun, args)
            # No return of result to model yet
          }
        },
        error = function(e) {
          message(e)
          send_text(paste("Error processing function call:", e$message))
        }
      )
    })

    evt <- reactive({
      fromJSON(req(input$key_event), simplifyVector = FALSE)
    })

    # Function to send events to the JS
    send <- function(events) {
      session$sendCustomMessage("realtime_send", events)
    }

    # Create return object
    result <- list(send = send, send_text = send_text, event = evt)

    # Add event emitter functionality
    result <- attach_event_emitter(result, evt)

    return(result)
  })
}
