#include "ScenarioLoader.h"
#include "Json.h"
#include "JsonUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "EngineUtils.h"

AScenarioLoader::AScenarioLoader()
{
    PrimaryActorTick.bCanEverTick = false;
}

void AScenarioLoader::BeginPlay()
{
    Super::BeginPlay();
}

bool AScenarioLoader::LoadScenario(const FString& FilePath, FScenarioConfig& OutConfig)
{
    // Read the JSON file from disk
    FString JsonString;
    if (!FFileHelper::LoadFileToString(JsonString, *FilePath))
    {
        UE_LOG(LogTemp, Error, TEXT("ScenarioLoader: Failed to load file: %s"), *FilePath);
        return false;
    }

    // Parse the JSON string
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);

    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("ScenarioLoader: Failed to parse JSON: %s"), *FilePath);
        return false;
    }

    // Read scenario_id
    OutConfig.ScenarioId = JsonObject->GetStringField(TEXT("scenario_id"));

    // Read object name
    OutConfig.ObjectName = JsonObject->GetStringField(TEXT("object"));

    // Read start_pose
    TSharedPtr<FJsonObject> StartPoseObj = JsonObject->GetObjectField(TEXT("start_pose"));
    OutConfig.StartPose.X = StartPoseObj->GetNumberField(TEXT("x"));
    OutConfig.StartPose.Y = StartPoseObj->GetNumberField(TEXT("y"));
    OutConfig.StartPose.Z = StartPoseObj->GetNumberField(TEXT("z"));

    // Read target_pose
    TSharedPtr<FJsonObject> TargetPoseObj = JsonObject->GetObjectField(TEXT("target_pose"));
    OutConfig.TargetPose.X = TargetPoseObj->GetNumberField(TEXT("x"));
    OutConfig.TargetPose.Y = TargetPoseObj->GetNumberField(TEXT("y"));
    OutConfig.TargetPose.Z = TargetPoseObj->GetNumberField(TEXT("z"));

    // Read tolerance and time
    OutConfig.PlacementToleranceMM = JsonObject->GetNumberField(TEXT("placement_tolerance_mm"));
    OutConfig.MaxCycleTimeSeconds = JsonObject->GetNumberField(TEXT("max_cycle_time_s"));

    UE_LOG(LogTemp, Log, TEXT("ScenarioLoader: Loaded scenario %s"), *OutConfig.ScenarioId);
    return true;
}

bool AScenarioLoader::ApplyScenario(const FScenarioConfig& Config)
{
    // Find the target object by name in the level
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        if (It->GetActorLabel().Contains(Config.ObjectName))
        {
            TargetActor = *It;
            break;
        }
    }

    if (!TargetActor)
    {
        UE_LOG(LogTemp, Error, TEXT("ScenarioLoader: Could not find actor: %s"), *Config.ObjectName);
        return false;
    }

    // Move the object to the start pose
    FVector StartLocation(Config.StartPose.X, Config.StartPose.Y, Config.StartPose.Z);
    TargetActor->SetActorLocation(StartLocation, false, nullptr, ETeleportType::TeleportPhysics);

    UE_LOG(LogTemp, Log, TEXT("ScenarioLoader: Applied scenario %s"), *Config.ScenarioId);
    return true;
}