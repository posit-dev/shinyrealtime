library(shiny)
library(htmltools)
library(jsonlite)
library(httr)
library(fontawesome)

# Create an HTMLDependency for the JS/CSS assets
realtimeDependency <- function() {
  htmlDependency(
    name = "shinyrealtime",
    version = "0.1.0",
    src = list(file = "www"),
    script = "app.js",
    stylesheet = "app.css"
  )
}

# UI Module
realtimeUI <- function(
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
          fa_i("microphone"),
          class = "btn btn-danger btn btn-mute",
          style = "width: 80px; display: none;"
        ),
        tags$button(
          fa_i("microphone-slash"),
          class = "btn btn-secondary btn btn-unmute",
          style = "width: 80px; display: none;"
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

# Server Module
realtimeServer <- function(
  id,
  # model = "gpt-4o-realtime-preview-2025-06-03",
  model = "gpt-realtime",
  voice = "alloy",
  instructions = NULL,
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
    send_text <- function(text) {
      event1 <- list(
        type = "conversation_item.create",
        item = list(
          role = "user",
          content = list(
            list(
              type = "input_text",
              text = text
            )
          )
        )
      )

      event2 <- list(
        type = "response.create",
        response = list()
      )

      send(list(event1, event2))
    }

    # Generate client secret from OpenAI
    output$key <- renderText({
      if (api_key == "") {
        stop("OPENAI_API_KEY environment variable is not set.")
      }

      provider <- chat_openai(model = "gpt-4.1-nano")$get_provider()
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
        url = "https://api.openai.com/v1/realtime/sessions",
        add_headers(
          Authorization = paste("Bearer", api_key),
          "Content-Type" = "application/json"
        ),
        body = req_body <<- toJSON(
          c(
            list(
              instructions = instructions,
              model = model,
              voice = voice,
              turn_detection = list(type = "semantic_vad"),
              tools = tool_schemas
            ),
            list(...)
          ),
          auto_unbox = TRUE
        ),
        encode = "json"
      )

      data <- content(res)
      if (!("client_secret" %in% names(data))) {
        print(data)
      }
      return(data$client_secret$value)
    })

    # Handle key events
    observeEvent(input$key_event, {
      tryCatch(
        {
          event <- evt()

          cat("-------------\n")
          cat(event$type, "\n")
          cat(input$key_event, "\n")

          if (event$type == "response.function_call_arguments.done") {
            fname <- event$name
            if (!fname %in% names(tools_by_name)) {
              stop(paste("Unknown function:", fname))
            }
            tool_fun <- tools_by_name[[fname]]
            args <- fromJSON(event$arguments)

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
    send <- function(...) {
      session$sendCustomMessage("realtime_send", list(...))
    }

    return(list(send = send, send_text = send_text, event = evt))
  })
}
