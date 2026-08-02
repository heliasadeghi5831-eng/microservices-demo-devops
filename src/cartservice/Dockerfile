ARG DOTNET_SDK_IMAGE=mcr.microsoft.com/dotnet/sdk:10.0
ARG DOTNET_RUNTIME_IMAGE=mcr.microsoft.com/dotnet/aspnet:10.0

FROM ${DOTNET_SDK_IMAGE} AS build

WORKDIR /source

COPY src/cartservice.csproj src/

RUN --mount=type=cache,id=cartservice-nuget,target=/root/.nuget/packages \
    dotnet restore src/cartservice.csproj \
    --disable-parallel \
    -p:NuGetAudit=false

COPY src/ src/

RUN --mount=type=cache,id=cartservice-nuget,target=/root/.nuget/packages \
    dotnet publish src/cartservice.csproj \
    --configuration Release \
    --output /app/publish \
    --no-restore \
    /p:UseAppHost=false

FROM ${DOTNET_RUNTIME_IMAGE} AS runtime

WORKDIR /app

COPY --from=build /app/publish ./

ENV ASPNETCORE_URLS=http://0.0.0.0:7070 \
    DOTNET_EnableDiagnostics=0

EXPOSE 7070

USER app

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/7070"]

ENTRYPOINT ["dotnet", "cartservice.dll"]
