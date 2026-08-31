from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.study import StudyContentNotFoundError, StudyGenerationError, generate_flashcards, generate_quiz
from app.api.schemas import FlashcardsResponse, QuizResponse, StudyRequest
from app.database.connection import get_db
from app.llm.provider import LLMNotConfiguredError, LLMProviderError

router = APIRouter()


@router.post("/study/quiz", response_model=QuizResponse)
def study_quiz(payload: StudyRequest, db: Session = Depends(get_db)):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    try:
        result = generate_quiz(db=db, query=payload.query, count=payload.count)
    except StudyContentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Couldn't find anything relevant to that topic in your uploaded documents.",
        )
    except StudyGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {exc}") from exc

    return result


@router.post("/study/flashcards", response_model=FlashcardsResponse)
def study_flashcards(payload: StudyRequest, db: Session = Depends(get_db)):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    try:
        result = generate_flashcards(db=db, query=payload.query, count=payload.count)
    except StudyContentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Couldn't find anything relevant to that topic in your uploaded documents.",
        )
    except StudyGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Flashcard generation failed: {exc}") from exc

    return result
