FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG PROJECT
WORKDIR /src

# Copy solution and projects
COPY AIVideoPlatform.sln ./
COPY src/ ./src/

# Restore dependencies
RUN dotnet restore

# Build and publish
WORKDIR /src/src/\$PROJECT
RUN dotnet publish -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
COPY --from=build /app/publish .

# Determine entrypoint from project name
ARG PROJECT
ENV DLL_NAME=\$PROJECT.dll
ENTRYPOINT dotnet \
